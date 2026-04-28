"""FastAPI server for disease prediction
Requirements: fastapi, uvicorn
Run with: uvicorn backend.api.server:app --reload --port 8000
"""
from backend.scripts.symptom_extractor import SymptomExtractor
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sys
import difflib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import uuid
import numpy as np
import pandas as pd
import xgboost as xgb

# Add backend/scripts to path to import predict
sys.path.insert(0, str(Path(__file__).resolve().parents[0].parents[0] / "scripts"))
from predict import predict_disease, build_model

# ── Session Store ─────────────────────────────────────────────────────────────
# In-memory session state: tracks confirmed symptoms and asked questions per session
# Structure: { session_id: {"symptoms": [...], "asked_questions": [...]} }
sessions: dict[str, dict] = {}

# Maximum follow-up questions before stopping and returning final prediction
# Hard stop: never ask more than 2 follow-up questions
MAX_FOLLOWUP_QUESTIONS = 2

# Confidence threshold: if top prediction >= this, stop asking questions
# Range: 0.0–1.0 (0.35 = 35% confidence)
# At 35% confidence, model is sufficiently certain to make a recommendation
CONFIDENCE_THRESHOLD = 0.35


# ── Request/Response Models ───────────────────────────────────────────────────
class PredictRequest(BaseModel):
    message: Optional[str] = None
    symptoms: Optional[list[str]] = None
    session_id: Optional[str] = None


class FollowupRequest(BaseModel):
    symptoms: Optional[list[str]] = None
    message: Optional[str] = None
    new_answer: dict  # e.g. {"chest_pain": 1}
    age: int = 30
    gender: str = "male"
    session_id: Optional[str] = None


class DiseaseResult(BaseModel):
    disease: str
    confidence: float


class ExplanationFactor(BaseModel):
    feature: str
    impact: float
    direction: str


class PredictResponse(BaseModel):
    detected_symptoms: list[str]
    top_predictions: list[dict]
    next_question: str | None
    next_symptom_key: str | None = None  # Symptom key for the next question (helps frontend avoid extraction)
    is_final: bool = False  # True if no more questions should be asked
    session_id: Optional[str] = None


# ── Follow-up Question Bank ───────────────────────────────────────────────────
# Curated questions for refining predictions
FOLLOWUP_QUESTIONS = {
    "respiratory": [
        "Do you have a cough?",
        "Are you experiencing shortness of breath?",
        "Do you feel tightness in your chest?",
    ],
    "cardiac": [
        "Do you have chest pain?",
        "Are you experiencing sweating?",
        "Do you feel arm pain or numbness?",
    ],
    "gastrointestinal": [
        "Do you have abdominal or stomach pain?",
        "Have you been vomiting?",
        "Have you experienced diarrhea?",
    ],
    "neurological": [
        "Do you have a headache?",
        "Are you feeling dizziness?",
        "Are you having trouble sleeping?",
    ],
    "general": [
        "Do you have a fever?",
        "Are you feeling unusually tired?",
        "Have you lost your appetite?",
    ],
}

SYMPTOM_QUESTION_MAP = {
    "cough": "Do you have a cough?",
    "shortness_of_breath": "Are you experiencing shortness of breath?",
    "chest_tightness": "Do you feel tightness in your chest?",
    "burning_chest_pain": "Do you have chest pain?",
    "sweating": "Are you experiencing sweating?",
    "arm_pain": "Do you feel arm pain?",
    "abdominal_pain": "Do you have abdominal pain?",
    "vomiting": "Have you been vomiting?",
    "diarrhea": "Have you experienced diarrhea?",
    "headache": "Do you have a headache?",
    "dizziness": "Are you feeling dizzy?",
    "insomnia": "Are you having trouble sleeping?",
    "fever": "Do you have a fever?",
    "fatigue": "Are you feeling unusually tired?",
    "loss_of_appetite": "Have you lost your appetite?",
    "nausea": "Are you feeling nauseous?",
    "throat_soreness": "Do you have a sore throat?",
    "joint_pain": "Do you have joint pain?",
    "back_pain": "Do you have back pain?",
    "skin_rash": "Do you have a skin rash?",
}

# ── REVERSE map: question text → symptom key (for strict matching) ──────────
QUESTION_SYMPTOM_MAP = {v: k for k, v in SYMPTOM_QUESTION_MAP.items()}


def load_env_file() -> None:
    """Load simple KEY=value pairs from .env without requiring python-dotenv."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def normalize_symptom(symptom: str) -> str:
    return symptom.lower().strip().replace(" ", "_").replace("-", "_")


def extract_symptoms_from_text(message: str, use_gemini_fallback: bool = True) -> list[str]:
    """
    Extract symptom keywords from free-text input using multi-strategy matching.
    Strategies: direct substring, synonym mapping, fuzzy matching, + optional Gemini fallback.
    
    Example:
        Input: "i feel very tired and have headache"
        Output: ["fatigue", "headache"]
    
    Args:
        message: User's free-text input
        use_gemini_fallback: If True and local strategies find no symptoms, use Gemini API
    """
    if not message:
        return []
    
    text_lower = message.lower()
    extracted = set()
    
    # Get all known symptoms
    known_symptoms = set(SYMPTOM_QUESTION_MAP.keys())
    
    # ── Strategy 1: Direct substring matching ──
    for symptom in known_symptoms:
        # Try space-separated version (e.g., "chest pain" for "chest_pain")
        symptom_str = symptom.replace("_", " ")
        if symptom_str in text_lower:
            extracted.add(symptom)
            continue
        
        # Try underscore version
        if symptom in text_lower:
            extracted.add(symptom)
    
    # ── Strategy 2: Synonym/abbreviation mapping ──
    # Common user phrases that map to known symptoms
    synonyms = {
        "tired": "fatigue",
        "tiredness": "fatigue",
        "exhausted": "fatigue",
        "weak": "fatigue",
        "weakness": "fatigue",
        "runny nose": "nasal_discharge",
        "stuffy nose": "nasal_discharge",
        "congestion": "nasal_discharge",
        "stomach pain": "abdominal_pain",
        "stomach ache": "abdominal_pain",
        "belly pain": "abdominal_pain",
        "throwing up": "vomiting",
        "throwing up": "vomiting",
        "sick": "nausea",
        "nauseous": "nausea",
        "dizzy": "dizziness",
        "light headed": "dizziness",
        "lightheaded": "dizziness",
        "sore throat": "throat_soreness",
        "scratchy throat": "throat_soreness",
        "difficulty sleeping": "insomnia",
        "can't sleep": "insomnia",
        "trouble sleeping": "insomnia",
        "sleepless": "insomnia",
        "chest discomfort": "burning_chest_pain",
        "chest pressure": "burning_chest_pain",
    }
    
    for phrase, symptom_key in synonyms.items():
        if phrase in text_lower and symptom_key in known_symptoms:
            extracted.add(symptom_key)
    
    # ── Strategy 3: Fuzzy matching on individual words ──
    # Extract meaningful words (longer than 2 chars, excluding common words)
    common_words = {"the", "and", "or", "i", "me", "my", "have", "has", "am", "is", "are", "feel", "feeling", "been", "very", "so", "too", "from", "with"}
    words = text_lower.replace(",", " ").replace("and", " ").split()
    
    for word in words:
        word = word.strip()
        # Skip very short or common words
        if len(word) <= 2 or word in common_words:
            continue
        
        # Skip if already matched directly
        if word in extracted:
            continue
        
        # Find close matches using fuzzy matching
        close_matches = difflib.get_close_matches(word, known_symptoms, n=1, cutoff=0.65)
        if close_matches:
            extracted.add(close_matches[0])
    
    # ── Strategy 4: Gemini API fallback (if enabled and no symptoms found) ──
    if not extracted and use_gemini_fallback:
        gemini_symptoms = generate_gemini_symptom_extraction(message)
        extracted.update(gemini_symptoms)
    
    # Return deduplicated, sorted list
    return sorted(list(extracted)) if extracted else []


def generate_gemini_symptom_extraction(message: str) -> list[str]:
    """
    Use Gemini API to extract medical symptoms from free-text user input.
    Validates extracted symptoms against known symptom list.
    
    Args:
        message: User's free-text symptom description
        
    Returns:
        List of normalized symptom keys that match SYMPTOM_QUESTION_MAP
        
    Example:
        Input: "I have fever and slight chest pain"
        Output: ["fever", "burning_chest_pain"]
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return []
    
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    known_symptoms = list(SYMPTOM_QUESTION_MAP.keys())
    
    prompt = {
        "user_input": message,
        "known_symptoms": known_symptoms,
        "task": (
            "Extract ONLY medical symptoms from this user input.\n\n"
            "Return a JSON array with symptom keys from the known_symptoms list.\n"
            "If a symptom is mentioned in a different way, find the closest match from known_symptoms.\n"
            "Do NOT include extra text or explanations.\n"
            "Return ONLY valid JSON array.\n\n"
            f"Known symptoms: {', '.join(known_symptoms)}\n\n"
            f"User input: \"{message}\"\n\n"
            "Return format: [\"symptom1\", \"symptom2\"]"
        ),
        "schema": ["string"],
    }
    
    payload = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt['task']}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.1,
            "maxOutputTokens": 256,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }).encode("utf-8")
    
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        
        # Parse JSON response
        try:
            symptoms = json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON array from text
            import re
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                symptoms = json.loads(match.group())
            else:
                return []
        
        # Validate that returned symptoms are in known list
        if isinstance(symptoms, list):
            valid_symptoms = [
                normalize_symptom(s) for s in symptoms
                if normalize_symptom(s) in known_symptoms
            ]
            return sorted(list(set(valid_symptoms)))
    
    except (KeyError, json.JSONDecodeError, TimeoutError, urllib.error.URLError):
        return []
    
    return []


def question_symptom(question: str) -> str | None:
    """
    Map a question text to its symptom key using STRICT matching.
    Returns None if question is not in the map.
    """
    return QUESTION_SYMPTOM_MAP.get(question)


def determine_confidence_level(top_confidence: float) -> str:
    """Determine confidence level based on top prediction probability."""
    if top_confidence >= 50:
        return "HIGH"
    elif top_confidence >= 30:
        return "MEDIUM"
    else:
        return "LOW"


def should_stop_asking(top_confidence: float, num_asked: int) -> bool:
    """
    Determine if we should stop asking follow-up questions.
    
    Stops if:
    1. Top prediction confidence >= CONFIDENCE_THRESHOLD, OR
    2. Already asked MAX_FOLLOWUP_QUESTIONS
    
    Args:
        top_confidence: Confidence of top prediction (0.0–1.0)
        num_asked: Number of questions already asked
        
    Returns:
        True if should stop asking, False otherwise
    """
    # Convert percentage to decimal if needed (e.g., 48 -> 0.48)
    conf = top_confidence / 100 if top_confidence > 1 else top_confidence
    
    if conf >= CONFIDENCE_THRESHOLD:
        print(f"[should_stop_asking] Confidence {conf:.2%} >= threshold {CONFIDENCE_THRESHOLD:.2%} → STOP")
        return True
    
    if num_asked >= MAX_FOLLOWUP_QUESTIONS:
        print(f"[should_stop_asking] Asked {num_asked} questions >= max {MAX_FOLLOWUP_QUESTIONS} → STOP")
        return True
    
    print(f"[should_stop_asking] Confidence {conf:.2%} < threshold, asked {num_asked}/{MAX_FOLLOWUP_QUESTIONS} → CONTINUE")
    return False


def select_next_question(predicted_diseases: list[str], already_asked: set[str] = None) -> str | None:
    """
    Generate a follow-up question based on predicted diseases.
    Uses STRICT symptom key matching to avoid repeats.
    
    Args:
        predicted_diseases: List of disease names from predictions
        already_asked: Set of symptom keys that have already been asked
        
    Returns:
        Question text, or None if all questions exhausted
    """
    if already_asked is None:
        already_asked = set()

    # Normalize the already_asked set to symptom keys
    asked_keys = {normalize_symptom(item) for item in already_asked}
    
    print(f"[select_next_question] Already asked: {asked_keys}")

    # Disease-category mapping for smarter question selection
    disease_categories = {
        "pneumonia": "respiratory",
        "bronchitis": "respiratory",
        "asthma": "respiratory",
        "tuberculosis": "respiratory",
        "influenza": "respiratory",
        "cold": "respiratory",
        "heart_failure": "cardiac",
        "coronary_artery_disease": "cardiac",
        "myocarditis": "cardiac",
        "gastritis": "gastrointestinal",
        "ulcer": "gastrointestinal",
        "appendicitis": "gastrointestinal",
        "migraine": "neurological",
        "epilepsy": "neurological",
        "anxiety": "neurological",
    }

    # Determine likely category from top predictions
    category = "general"
    for disease in predicted_diseases:
        disease_lower = disease.lower()
        for key, cat in disease_categories.items():
            if key in disease_lower:
                category = cat
                break
        if category != "general":
            break

    print(f"[select_next_question] Predicted category: {category}")

    # Build list of questions for this category, in order
    category_questions = FOLLOWUP_QUESTIONS.get(category, FOLLOWUP_QUESTIONS["general"])
    
    # Iterate through questions and return the first one whose symptom hasn't been asked
    for question in category_questions:
        symptom_key = question_symptom(question)
        if symptom_key is None:
            print(f"[select_next_question] WARNING: Question '{question}' has no symptom mapping!")
            continue
        if symptom_key not in asked_keys:
            print(f"[select_next_question] Selected: '{question}' (symptom: {symptom_key})")
            return question

    # Fallback: try general questions
    print(f"[select_next_question] Category exhausted, trying general questions")
    for question in FOLLOWUP_QUESTIONS["general"]:
        symptom_key = question_symptom(question)
        if symptom_key is None:
            print(f"[select_next_question] WARNING: Question '{question}' has no symptom mapping!")
            continue
        if symptom_key not in asked_keys:
            print(f"[select_next_question] Selected (fallback): '{question}' (symptom: {symptom_key})")
            return question

    print(f"[select_next_question] No more questions available")
    return None


def get_next_question(session: dict, predicted_diseases: list[str]) -> tuple[str | None, str | None]:
    """
    Return the next (question, symptom_key) that hasn't been asked yet in this session.
    Delegates to select_next_question for disease-aware ordering, then falls back
    to iterating SYMPTOM_QUESTION_MAP so we never repeat.
    """
    asked = set(session["asked_questions"])
    confirmed = set(session["symptoms"])
    excluded = asked | confirmed

    # Try disease-aware selection first
    fallback_q = select_next_question(predicted_diseases, excluded)
    if fallback_q:
        sym = question_symptom(fallback_q)
        return fallback_q, sym

    # Exhaustive fallback: walk every known symptom in order
    for sym, question in SYMPTOM_QUESTION_MAP.items():
        if sym not in excluded:
            return question, sym

    return None, None


def build_feature_row(symptoms: list[str], age: int, gender: str, feature_cols: list[str]) -> tuple[pd.DataFrame, list[str]]:
    row = {col: 0 for col in feature_cols}
    row["age"] = age
    row["gender_male"] = 1 if gender.lower() == "male" else 0
    row["gender_female"] = 1 if gender.lower() != "male" else 0

    synonyms = {
        "cold": "common_cold_symptoms",
        "runny_nose": "nasal_discharge",
        "stomach_ache": "abdominal_pain",
        "stomach_pain": "abdominal_pain",
        "chest_pain": "burning_chest_pain",
        "throwing_up": "vomiting",
        "throw_up": "vomiting",
        "dizzy": "dizziness",
        "tired": "fatigue",
        "tired_all_the_time": "fatigue",
        "cant_sleep": "insomnia",
        "no_appetite": "loss_of_appetite",
        "back_ache": "back_pain",
        "sore_throat": "throat_soreness",
    }

    matched = []
    for symptom in symptoms:
        col = synonyms.get(normalize_symptom(symptom), normalize_symptom(symptom))
        if col in row:
            row[col] = 1
            matched.append(col)
            continue

        close = difflib.get_close_matches(col, feature_cols, n=1, cutoff=0.6)
        if close:
            row[close[0]] = 1
            matched.append(close[0])

    X_input = pd.DataFrame([row])[feature_cols]
    X_input = X_input.apply(pd.to_numeric, errors="coerce").fillna(0)
    return X_input, matched


def explain_prediction(symptoms: list[str], age: int, gender: str, artifacts: dict, predictions: list[dict]) -> tuple[str, list[ExplanationFactor]]:
    X_input, matched = build_feature_row(symptoms, age, gender, artifacts["feature_cols"])
    factors: list[ExplanationFactor] = []

    try:
        X_svd = artifacts["svd"].transform(X_input)
        X_scaled = artifacts["scaler"].transform(X_svd)
        booster = artifacts["model"].get_booster()
        contribs = booster.predict(xgb.DMatrix(X_scaled), pred_contribs=True)
        top_idx = int(np.argmax(artifacts["model"].predict_proba(X_scaled)[0]))
        class_contribs = contribs[0, top_idx, :-1] if contribs.ndim == 3 else contribs[0, :-1]
        original_contribs = np.dot(class_contribs, artifacts["svd"].components_)

        for symptom in matched:
            if symptom in artifacts["feature_cols"]:
                idx = artifacts["feature_cols"].index(symptom)
                impact = float(original_contribs[idx])
                factors.append(
                    ExplanationFactor(
                        feature=symptom,
                        impact=round(abs(impact), 4),
                        direction="supports" if impact >= 0 else "lowers",
                    )
                )
    except Exception:
        factors = []

    if not factors:
        factors = [
            ExplanationFactor(feature=symptom, impact=1.0, direction="present")
            for symptom in matched[:5]
        ]

    factors = sorted(factors, key=lambda item: item.impact, reverse=True)[:5]
    factor_names = [factor.feature.replace("_", " ") for factor in factors]
    top = predictions[0]["disease"] if predictions else "the top prediction"
    explanation = (
        f"{top} was ranked highest mainly from the confirmed pattern: "
        f"{', '.join(factor_names)}."
        if factor_names
        else f"{top} was ranked highest by the model, but no individual symptom factors were available."
    )
    return explanation, factors


def generate_gemini_followup(
    symptoms: list[str],
    asked_symptoms: set[str],
    predictions: list[dict],
    fallback_question: str | None,
) -> tuple[str | None, str | None]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None, None

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    confirmed = {normalize_symptom(symptom) for symptom in symptoms}
    asked = {normalize_symptom(symptom) for symptom in asked_symptoms}
    candidate_symptoms = [
        {"symptom": symptom, "question": question}
        for symptom, question in SYMPTOM_QUESTION_MAP.items()
        if symptom not in confirmed and symptom not in asked
    ]
    prompt = {
        "symptoms": symptoms,
        "already_asked_symptoms": sorted(asked),
        "allowed_candidates": candidate_symptoms,
        "top_predictions": predictions,
        "fallback_question": fallback_question,
        "task": (
            "You are a friendly, conversational medical assistant.\n\n"
            "Your job is ONLY to ask about a specific symptom in a natural, human-like way.\n\n"
            "Instructions:\n"
            "- Ask ONLY ONE question\n"
            "- Keep it under 20 words\n"
            "- Make it sound natural and human\n"
            "- Clearly refer to the symptom you're asking about\n"
            "- Use a natural transition (e.g., 'That helps...', 'Just to check...')\n"
            "- Avoid repeating previous wording\n"
            "- Vary sentence structure\n"
            "- Do NOT diagnose or mention diseases\n"
            "- Do NOT introduce new symptoms\n\n"
            "Tone: Friendly, calm, slightly conversational, clear and simple.\n\n"
            "Examples of natural variations:\n"
            "- 'That helps. Have you noticed any chest discomfort?'\n"
            "- 'Just to check, are you experiencing any chest pain?'\n"
            "- 'Okay, one more thing — any discomfort in your chest?'\n\n"
            "Return exactly one JSON object with keys 'symptom' and 'question'."
        ),
        "schema": {"symptom": "string", "question": "string"},
    }
    payload = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": json.dumps(prompt)}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.2,
            "maxOutputTokens": 512,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            parsed = json.loads(text[start:end + 1]) if start != -1 and end != -1 else {"question": text}

        question = str(parsed.get("question", "")).strip()
        symptom = normalize_symptom(str(parsed.get("symptom", "")).strip())
        allowed = {item["symptom"] for item in candidate_symptoms}
        if question and question.endswith("?") and symptom in allowed:
            return question, symptom
    except (KeyError, json.JSONDecodeError, TimeoutError, urllib.error.URLError):
        return None, None

    return None, None


# ── Lifespan Event Handler ────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup, cleanup on shutdown."""
    load_env_file()
    print("Loading model on startup...")
    artifacts = build_model()
    app.state.artifacts = {
        "model": artifacts[0],
        "svd": artifacts[1],
        "scaler": artifacts[2],
        "le": artifacts[3],
        "feature_cols": artifacts[4],
        "original_classes": artifacts[5],
    }
    print("Model loaded successfully.")
    yield
    # Cleanup on shutdown (nothing needed)
    print("Shutting down...")


# ── FastAPI App ───────────────────────────────────────────────────────────────
# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(title="FairMed AI Disease Predictor", lifespan=lifespan)

# Enable CORS for frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # This allows all origins and solves most local dev issues
    allow_credentials=False, # Must be False if allow_origins is "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Endpoints ──────────────────────────────────────────────────────────────────
def smart_extract(text: str) -> list[str]:
    local_extractor = SymptomExtractor()
    local_results = local_extractor.extract_and_score(text)

    if not local_results:
        return extract_symptoms_gemini(text)

    avg_conf = sum(r['confidence'] for r in local_results) / len(local_results)

    if avg_conf < 0.75:
        try:
            return extract_symptoms_gemini(text)
        except:
            return [r['symptom'] for r in local_results]

    return [r['symptom'] for r in local_results]


@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """
    Predict diseases from symptoms. Initializes a session for follow-up tracking.
    """
    if request.message:
        symptoms = smart_extract(request.message)
    elif request.symptoms:
        symptoms = request.symptoms
    else:
        raise HTTPException(status_code=400, detail="No input")

    try:
        artifacts = app.state.artifacts

        predictions = predict_disease(
            symptoms=symptoms,
            age=30,
            gender="male",
            model=artifacts["model"],
            svd=artifacts["svd"],
            scaler=artifacts["scaler"],
            le=artifacts["le"],
            feature_cols=artifacts["feature_cols"],
            original_classes=artifacts["original_classes"],
            top_k=3,
        )

        if not predictions:
            raise HTTPException(
                status_code=422,
                detail="None of the provided symptoms were recognized",
            )

        print(f"[/predict] Symptoms: {symptoms}")
        print(f"[/predict] Predictions: {[(p['disease'], p['confidence']) for p in predictions]}")

        # ── Initialize session ────────────────────────────────────────────────
        session_id = request.session_id or str(uuid.uuid4())
        sessions[session_id] = {
            "symptoms": list(symptoms),
            "asked_questions": [],
        }
        session = sessions[session_id]

        predicted_disease_names = [p["disease"] for p in predictions]
        
        # ── Check if we should stop asking based on confidence ────────────────
        top_confidence = predictions[0]["confidence"]
        is_final = should_stop_asking(top_confidence, len(session["asked_questions"]))
        
        next_question = None
        next_sym = None
        
        if not is_final:
            # Only ask more questions if confidence is low
            fallback_question, next_sym = get_next_question(session, predicted_disease_names)

            gemini_question, gemini_sym = generate_gemini_followup(
                symptoms,
                set(session["asked_questions"]) | set(session["symptoms"]),
                predictions,
                fallback_question,
            )

            if gemini_question and gemini_sym:
                next_question = gemini_question
                next_sym = gemini_sym
            else:
                next_question = fallback_question

            # Record the question we're about to ask
            if next_sym and next_sym not in session["asked_questions"]:
                session["asked_questions"].append(next_sym)
        else:
            print(f"[/predict] Prediction is final, not asking more questions")

        response = {
            "detected_symptoms": symptoms,
            "top_predictions": predictions,
            "next_question": next_question,
            "next_symptom_key": next_sym,  # Include symptom key to avoid frontend extraction errors
            "is_final": is_final,
        }
        # Attach session_id so the frontend can send it back
        response["session_id"] = session_id  # type: ignore[assignment]
        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/followup", response_model=PredictResponse)
async def followup(request: FollowupRequest):
    """
    Get updated predictions based on follow-up answer.
    Uses session memory to avoid repeating questions.
    """
    # ── Resolve session ───────────────────────────────────────────────────────
    session_id = request.session_id or "default"
    session = sessions.get(session_id)

    # Fallback: reconstruct session from request if not found
    if session is None:
        base_symptoms = list(request.symptoms or [])
        if not base_symptoms and request.message:
            base_symptoms = extract_symptoms_from_text(request.message)
        session = {"symptoms": base_symptoms, "asked_questions": []}
        sessions[session_id] = session

    # ── Process the new answer ────────────────────────────────────────────────
    if request.new_answer:
        sym = list(request.new_answer.keys())[0]
        print(f"[/followup] User answered about symptom: {sym}")
        # Add to confirmed symptoms if answered yes (value == 1)
        if request.new_answer[sym] == 1 and sym not in session["symptoms"]:
            session["symptoms"].append(sym)
            print(f"[/followup] Added to confirmed symptoms: {sym}")
        # Always mark as asked so we never repeat it
        if sym not in session["asked_questions"]:
            session["asked_questions"].append(sym)
            print(f"[/followup] Marked as asked: {sym}")
        else:
            print(f"[/followup] Already marked as asked: {sym}")

    new_symptoms = list(session["symptoms"])

    if not new_symptoms:
        raise HTTPException(
            status_code=400,
            detail="No symptoms available. Start a new conversation with /predict.",
        )

    try:
        artifacts = app.state.artifacts

        predictions = predict_disease(
            symptoms=new_symptoms,
            age=request.age,
            gender=request.gender,
            model=artifacts["model"],
            svd=artifacts["svd"],
            scaler=artifacts["scaler"],
            le=artifacts["le"],
            feature_cols=artifacts["feature_cols"],
            original_classes=artifacts["original_classes"],
            top_k=3,
        )

        if not predictions:
            raise HTTPException(
                status_code=422,
                detail="None of the provided symptoms were recognized",
            )

        print(f"[/followup] Symptoms: {new_symptoms}")
        print(f"[/followup] Asked so far: {session['asked_questions']}")
        print(f"[/followup] Predictions: {[(p['disease'], p['confidence']) for p in predictions]}")

        predicted_disease_names = [p["disease"] for p in predictions]

        # ── Check if we should stop asking based on confidence ────────────────
        top_confidence = predictions[0]["confidence"]
        is_final = should_stop_asking(top_confidence, len(session["asked_questions"]))
        
        next_question = None
        next_sym = None
        
        if not is_final:
            # Only ask more questions if confidence is low
            fallback_question, next_sym = get_next_question(session, predicted_disease_names)

            gemini_question, gemini_sym = generate_gemini_followup(
                new_symptoms,
                set(session["asked_questions"]) | set(session["symptoms"]),
                predictions,
                fallback_question,
            )

            if gemini_question and gemini_sym:
                next_question = gemini_question
                next_sym = gemini_sym
            else:
                next_question = fallback_question

            # Record the question we're about to ask
            if next_sym and next_sym not in session["asked_questions"]:
                session["asked_questions"].append(next_sym)
        else:
            print(f"[/followup] Prediction is final, not asking more questions")

        response = PredictResponse(
            detected_symptoms=new_symptoms,
            top_predictions=predictions,
            next_question=next_question,
            next_symptom_key=next_sym,  # Include symptom key to avoid frontend extraction errors
            is_final=is_final,
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


def test_bias():
    """Basic bias check: compare predictions for same symptoms across genders."""
    artifacts = None
    try:
        built = build_model()
        artifacts = {
            "model": built[0], "svd": built[1], "scaler": built[2],
            "le": built[3], "feature_cols": built[4], "original_classes": built[5],
        }
    except Exception as e:
        print(f"[test_bias] Could not load model: {e}")
        return

    symptoms = ["fever", "cough"]
    for gender in ("male", "female"):
        preds = predict_disease(
            symptoms=symptoms, age=30, gender=gender,
            model=artifacts["model"], svd=artifacts["svd"],
            scaler=artifacts["scaler"], le=artifacts["le"],
            feature_cols=artifacts["feature_cols"],
            original_classes=artifacts["original_classes"], top_k=3,
        )
        print(f"[test_bias] {gender.capitalize()}: {[(p['disease'], round(p['confidence'], 1)) for p in preds]}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

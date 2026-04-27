"""FastAPI server for disease prediction
Requirements: fastapi, uvicorn
Run with: uvicorn backend.api.server:app --reload --port 8000
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import difflib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

# Add backend/scripts to path to import predict
sys.path.insert(0, str(Path(__file__).resolve().parents[0].parents[0] / "scripts"))
from predict import predict_disease, build_model


# ── Request/Response Models ───────────────────────────────────────────────────
class PredictRequest(BaseModel):
    symptoms: list[str]
    asked_symptoms: list[str] = []
    age: int = 30
    gender: str = "male"


class FollowupRequest(BaseModel):
    symptoms: list[str]
    new_answer: dict  # e.g. {"chest_pain": 1}
    age: int = 30
    gender: str = "male"


class DiseaseResult(BaseModel):
    disease: str
    confidence: float


class ExplanationFactor(BaseModel):
    feature: str
    impact: float
    direction: str


class PredictResponse(BaseModel):
    top_predictions: list[DiseaseResult]
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    next_question: str | None  # e.g. "Do you have chest pain?"
    next_symptom: str | None = None
    question_source: str = "rules"
    explanation: str | None = None
    explanation_factors: list[ExplanationFactor] = []


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


def question_symptom(question: str) -> str | None:
    for symptom, mapped_question in SYMPTOM_QUESTION_MAP.items():
        if mapped_question == question:
            return symptom
    return None


def determine_confidence_level(top_confidence: float) -> str:
    """Determine confidence level based on top prediction probability."""
    if top_confidence >= 50:
        return "HIGH"
    elif top_confidence >= 30:
        return "MEDIUM"
    else:
        return "LOW"


def select_next_question(predicted_diseases: list[str], already_asked: set[str] = None) -> str | None:
    """
    Generate a follow-up question based on predicted diseases.
    Prioritize questions related to the top predictions.
    """
    if already_asked is None:
        already_asked = set()

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

    already_asked = {normalize_symptom(item) for item in already_asked}

    # Select from category questions
    questions = FOLLOWUP_QUESTIONS.get(category, FOLLOWUP_QUESTIONS["general"])
    for question in questions:
        symptom = question_symptom(question)
        if question not in already_asked and symptom not in already_asked:
            return question

    # Fallback to general questions
    for question in FOLLOWUP_QUESTIONS["general"]:
        symptom = question_symptom(question)
        if question not in already_asked and symptom not in already_asked:
            return question

    return None


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
app = FastAPI(title="FairMed AI Disease Predictor", lifespan=lifespan)

# Enable CORS for all origins (frontend will be on localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ──────────────────────────────────────────────────────────────────
@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """
    Predict diseases from symptoms.

    Request:
        symptoms: List of symptom strings
        age: Patient age (default 30)
        gender: 'male' or 'female' (default 'male')

    Response:
        top_predictions: List of top-3 disease predictions with confidence
        confidence: Confidence level (HIGH, MEDIUM, LOW)
        next_question: Follow-up question to refine prediction, or None
    """

    # Validate input
    if not request.symptoms or len(request.symptoms) == 0:
        raise HTTPException(status_code=400, detail="No symptoms provided")

    try:
        # Get artifacts from app state
        artifacts = app.state.artifacts

        # Call predict_disease
        predictions = predict_disease(
            symptoms=request.symptoms,
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

        # Check if at least one symptom matched
        if not predictions:
            raise HTTPException(
                status_code=422,
                detail="None of the provided symptoms were recognized",
            )

        # Format predictions
        formatted_predictions = [
            DiseaseResult(disease=p["disease"], confidence=p["confidence"])
            for p in predictions
        ]

        # Determine confidence level
        top_confidence = predictions[0]["confidence"]
        confidence_level = determine_confidence_level(top_confidence)

        # Generate next question based on top predictions
        predicted_disease_names = [p["disease"] for p in predictions]
        already_asked = set(request.symptoms) | set(request.asked_symptoms)
        fallback_question = select_next_question(predicted_disease_names, already_asked)
        fallback_symptom = question_symptom(fallback_question) if fallback_question else None
        gemini_question, gemini_symptom = generate_gemini_followup(
            request.symptoms,
            already_asked,
            predictions,
            fallback_question,
        )
        next_question = gemini_question or fallback_question
        next_symptom = gemini_symptom or fallback_symptom
        explanation, explanation_factors = explain_prediction(
            request.symptoms,
            request.age,
            request.gender,
            artifacts,
            predictions,
        )

        return PredictResponse(
            top_predictions=formatted_predictions,
            confidence=confidence_level,
            next_question=next_question,
            next_symptom=next_symptom,
            question_source="gemini" if gemini_question else "rules",
            explanation=explanation,
            explanation_factors=explanation_factors,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/followup", response_model=PredictResponse)
async def followup(request: FollowupRequest):
    """
    Get updated predictions based on follow-up answer.

    Request:
        symptoms: Original list of symptom strings
        new_answer: Dict with newly confirmed symptom (e.g. {"chest_pain": 1})
        age: Patient age
        gender: Patient gender

    Response:
        Updated predictions with confidence and next question
    """

    # Validate input
    if not request.symptoms or len(request.symptoms) == 0:
        raise HTTPException(status_code=400, detail="No symptoms provided")

    try:
        # Add new symptom to the list
        new_symptoms = list(request.symptoms)
        
        # Extract the symptom name from new_answer
        # new_answer format: {"symptom_name": 1}
        if request.new_answer:
            new_sym = list(request.new_answer.keys())[0]
            if request.new_answer[new_sym] == 1 and new_sym not in new_symptoms:
                new_symptoms.append(new_sym)

        # Get artifacts from app state
        artifacts = app.state.artifacts

        # Call predict_disease with updated symptoms
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

        # Check if at least one symptom matched
        if not predictions:
            raise HTTPException(
                status_code=422,
                detail="None of the provided symptoms were recognized",
            )

        # Format predictions
        formatted_predictions = [
            DiseaseResult(disease=p["disease"], confidence=p["confidence"])
            for p in predictions
        ]

        # Determine confidence level
        top_confidence = predictions[0]["confidence"]
        confidence_level = determine_confidence_level(top_confidence)

        # Generate next question (avoid previous symptoms)
        predicted_disease_names = [p["disease"] for p in predictions]
        already_asked = set(request.symptoms) | set(request.new_answer.keys())
        fallback_question = select_next_question(predicted_disease_names, already_asked)
        fallback_symptom = question_symptom(fallback_question) if fallback_question else None
        gemini_question, gemini_symptom = generate_gemini_followup(
            new_symptoms,
            already_asked,
            predictions,
            fallback_question,
        )
        next_question = gemini_question or fallback_question
        next_symptom = gemini_symptom or fallback_symptom
        explanation, explanation_factors = explain_prediction(
            new_symptoms,
            request.age,
            request.gender,
            artifacts,
            predictions,
        )

        return PredictResponse(
            top_predictions=formatted_predictions,
            confidence=confidence_level,
            next_question=next_question,
            next_symptom=next_symptom,
            question_source="gemini" if gemini_question else "rules",
            explanation=explanation,
            explanation_factors=explanation_factors,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

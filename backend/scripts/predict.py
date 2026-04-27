"""
Disease Prediction from Symptoms
Usage:
    python backend/scripts/predict.py

Or import and call predict_disease() directly from your app.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import difflib
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
import warnings
import joblib
import os
import sys
warnings.filterwarnings("ignore")

RANDOM_STATE = 42
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
MODEL_DIR = ROOT / "models" / "artifacts"
PROTECTED = ["age", "gender_female", "gender_male"]


def save_artifacts(model, svd, scaler, le, feature_cols, original_classes):
    """Save all model artifacts to disk."""
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_DIR / "xgb_model.pkl")
    joblib.dump(svd, MODEL_DIR / "svd.pkl")
    joblib.dump(scaler, MODEL_DIR / "scaler.pkl")
    joblib.dump(le, MODEL_DIR / "label_encoder.pkl")
    joblib.dump(feature_cols, MODEL_DIR / "feature_cols.pkl")
    joblib.dump(original_classes, MODEL_DIR / "original_classes.pkl")
    print("Model artifacts saved to disk.")


def load_artifacts():
    """Load all model artifacts from disk. Returns None if not found."""
    try:
        model = joblib.load(MODEL_DIR / "xgb_model.pkl")
        svd = joblib.load(MODEL_DIR / "svd.pkl")
        scaler = joblib.load(MODEL_DIR / "scaler.pkl")
        le = joblib.load(MODEL_DIR / "label_encoder.pkl")
        feature_cols = joblib.load(MODEL_DIR / "feature_cols.pkl")
        original_classes = joblib.load(MODEL_DIR / "original_classes.pkl")
        print("Model artifacts loaded from disk.")
        return model, svd, scaler, le, feature_cols, original_classes
    except FileNotFoundError:
        return None


def build_model():
    """Load from disk if available, otherwise train and save."""
    cached = load_artifacts()
    if cached is not None:
        return cached
    
    print("No saved model found. Training from scratch...")

    print("Loading data and training model...")

    X_train_raw = pd.read_csv(DATA_DIR / "fair_X_train.csv")
    y_train_raw = pd.read_csv(DATA_DIR / "y_train_labels.csv").iloc[:, 0]
    with open(DATA_DIR / "preprocessing_metadata.json", "r") as f:
        meta = json.load(f)

    original_classes = np.array(meta["classes"])  # 773 disease string names

    # Filter top-50
    top_classes = y_train_raw.value_counts().head(50).index
    mask = y_train_raw.isin(top_classes)
    X_full = X_train_raw[mask].reset_index(drop=True)
    y_full = y_train_raw[mask].reset_index(drop=True)

    X_train, _, y_train, _ = train_test_split(
        X_full, y_full, test_size=0.2, stratify=y_full, random_state=RANDOM_STATE
    )
    X_train = X_train.reset_index(drop=True)
    y_train = y_train.reset_index(drop=True)

    # Sample for speed
    if len(X_train) > 20000:
        idx_per_class = y_train.groupby(y_train).head(1).index
        remaining_idx = y_train.drop(index=idx_per_class).sample(
            n=20000 - len(idx_per_class), random_state=RANDOM_STATE
        ).index
        sample_idx = idx_per_class.union(remaining_idx)
        X_train = X_train.loc[sample_idx].reset_index(drop=True)
        y_train = y_train.loc[sample_idx].reset_index(drop=True)

    le = LabelEncoder()
    y_train_enc = le.fit_transform(y_train)

    # Drop protected for base features (we use full features for XGBoost)
    X_train_full = X_train.copy()
    feature_cols = X_train_full.columns.tolist()

    # SVD + Scaler
    svd = TruncatedSVD(n_components=50, random_state=RANDOM_STATE)
    X_svd = svd.fit_transform(X_train_full)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_svd)

    # Early stopping split
    X_tr, X_val, y_tr, y_val = train_test_split(
        X_scaled, y_train_enc, test_size=0.2, random_state=RANDOM_STATE
    )

    model = XGBClassifier(
        objective='multi:softprob',
        num_class=len(le.classes_),
        n_estimators=200,
        max_depth=8,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1,
        reg_alpha=0.5,
        early_stopping_rounds=20,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        verbosity=0
    )
    model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
    print("Model ready.")

    save_artifacts(model, svd, scaler, le, feature_cols, original_classes)

    return model, svd, scaler, le, feature_cols, original_classes


def predict_disease(symptoms: list, age: int = 30, gender: str = "male",
                    model=None, svd=None, scaler=None,
                    le=None, feature_cols=None, original_classes=None,
                    top_k: int = 3):
    """
    Predict top-k diseases from a list of symptom strings.

    Args:
        symptoms:         List of symptom strings e.g. ['fever', 'headache', 'cough']
        age:              Patient age (default 30)
        gender:           'male' or 'female' (default 'male')
        model, svd, ...   Pass pre-built model artifacts (avoids retraining)
        top_k:            Number of top predictions to return (default 3)

    Returns:
        List of dicts: [{'disease': str, 'confidence': float}, ...]
    """

    # Build a zero feature vector
    row = {col: 0 for col in feature_cols}

    # Fill age and gender
    row['age'] = age
    if gender.lower() == 'male':
        row['gender_male'] = 1
        row['gender_female'] = 0
    else:
        row['gender_male'] = 0
        row['gender_female'] = 1

    # Fill symptoms — normalize input to match column format
    def normalize(s):
        return s.lower().strip().replace(' ', '_').replace('-', '_')

    SYNONYMS = {
        "cold": "common_cold_symptoms",
        "runny_nose": "nasal_discharge",
        "stomach_ache": "abdominal_pain",
        "stomach_pain": "abdominal_pain",
        "chest_pain": "burning_chest_pain",
        "shortness_of_breath": "shortness_of_breath",
        "throwing_up": "vomiting",
        "throw_up": "vomiting",
        "dizzy": "dizziness",
        "tired": "fatigue",
        "tired_all_the_time": "fatigue",
        "cant_sleep": "insomnia",
        "no_appetite": "loss_of_appetite",
        "skin_rash": "skin_rash",
        "joint_pain": "joint_pain",
        "back_ache": "back_pain",
        "headache": "headache",
        "sore_throat": "throat_soreness",
    }

    valid_symptoms = []
    unrecognized = []
    for sym in symptoms:
        col = normalize(sym)
        # Apply synonym map
        if col in SYNONYMS:
            col = SYNONYMS[col]
        if col in row:
            row[col] = 1
            valid_symptoms.append(col)
        else:
            # Fuzzy match
            close = difflib.get_close_matches(col, feature_cols, n=1, cutoff=0.6)
            if close:
                row[close[0]] = 1
                valid_symptoms.append(close[0])
                print(f"  [Matched] '{sym}' -> '{close[0]}'")
            else:
                unrecognized.append(sym)

    if unrecognized:
        print(f"  [Warning] Unrecognized symptoms (ignored): {unrecognized}")
    if not valid_symptoms:
        print("  [Error] No valid symptoms provided.")
        return []

    # Build input DataFrame
    X_input = pd.DataFrame([row])[feature_cols]
    X_input = X_input.apply(pd.to_numeric, errors='coerce').fillna(0)

    # Transform
    X_svd = svd.transform(X_input)
    X_scaled = scaler.transform(X_svd)

    # Predict
    probs = model.predict_proba(X_scaled)[0]
    top_k_indices = np.argsort(probs)[::-1][:top_k]

    results = []
    for idx in top_k_indices:
        encoded_label = le.classes_[idx]       # integer code (0-49 range in le space)
        # Map back to original disease string via le.inverse_transform → original int → string
        original_int = le.inverse_transform([idx])[0]  # gets the preprocess.py integer
        disease_name = original_classes[original_int]   # gets the string name
        confidence = float(probs[idx])
        results.append({
            "disease": disease_name.title(),
            "confidence": round(confidence * 100, 2)
        })

    return results


# ── MAIN (interactive demo) ───────────────────────────────────────────────────
if __name__ == "__main__":

    # Check for force retrain flag
    force_retrain = "--retrain" in sys.argv
    if force_retrain and MODEL_DIR.exists():
        import shutil
        shutil.rmtree(MODEL_DIR)
        print("Cleared saved artifacts. Retraining...")

    # Build model once
    model, svd, scaler, le, feature_cols, original_classes = build_model()

    print("\n" + "="*50)
    print("  FairMed AI — Disease Prediction")
    print("="*50)
    print("Enter symptoms separated by commas.")
    print("Type 'quit' to exit.\n")

    # Quick demo
    demo_cases = [
        {
            "symptoms": ["fever", "cough", "fatigue", "shortness_of_breath"],
            "age": 35,
            "gender": "male",
            "label": "Demo 1 (respiratory)"
        },
        {
            "symptoms": ["burning_chest_pain", "sweating", "nausea", "arm_pain"],
            "age": 55,
            "gender": "male",
            "label": "Demo 2 (cardiac)"
        },
        {
            "symptoms": ["acne_or_pimples", "too_little_hair", "dizziness"],
            "age": 22,
            "gender": "female",
            "label": "Demo 3 (skin)"
        },
    ]

    for case in demo_cases:
        print(f"\n--- {case['label']} ---")
        print(f"Symptoms : {case['symptoms']}")
        print(f"Patient  : Age {case['age']}, {case['gender'].title()}")
        predictions = predict_disease(
            symptoms=case["symptoms"],
            age=case["age"],
            gender=case["gender"],
            model=model, svd=svd, scaler=scaler,
            le=le, feature_cols=feature_cols,
            original_classes=original_classes
        )
        print("Top-3 Predictions:")
        for i, p in enumerate(predictions, 1):
            print(f"  {i}. {p['disease']:<40} {p['confidence']}%")

    # Interactive mode
    print("\n" + "="*50)
    print("Interactive Mode")
    print("="*50)
    while True:
        raw = input("\nEnter symptoms (comma separated) or 'quit': ").strip()
        if raw.lower() == 'quit':
            break
        age_input = input("Age (default 30): ").strip()
        gender_input = input("Gender male/female (default male): ").strip()

        age = int(age_input) if age_input.isdigit() else 30
        gender = gender_input if gender_input in ["male", "female"] else "male"
        # Normalize natural language input
        raw_cleaned = raw.lower()
        raw_cleaned = raw_cleaned.replace(' and ', ',').replace(' with ', ',')
        raw_cleaned = raw_cleaned.replace(' also ', ',').replace(' plus ', ',')
        symptoms = [s.strip() for s in raw_cleaned.split(",") if s.strip()]

        predictions = predict_disease(
            symptoms=symptoms,
            age=age,
            gender=gender,
            model=model, svd=svd, scaler=scaler,
            le=le, feature_cols=feature_cols,
            original_classes=original_classes
        )

        print("\nTop-3 Predictions:")
        for i, p in enumerate(predictions, 1):
            print(f"  {i}. {p['disease']:<40} {p['confidence']}%")

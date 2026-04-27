import json
import pandas as pd
import numpy as np
import os
from sklearn.preprocessing import LabelEncoder
from pathlib import Path

ROOT = Path("backend")
DATA_DIR = ROOT / "data" / "processed"
REPORT_PATH = ROOT / "models" / "model_evaluation_report.json"

# 1. LOAD DATA
X_train = pd.read_csv(DATA_DIR / "fair_X_train.csv")
y_train = pd.read_csv(DATA_DIR / "y_train_labels.csv").squeeze("columns")
X_test = pd.read_csv(DATA_DIR / "fair_X_test_patient.csv")
y_test = pd.read_csv(DATA_DIR / "fair_y_test_patient.csv").squeeze("columns")

# FILTER TOP FREQUENT DISEASES
top_classes = y_train.value_counts().head(50).index

mask_train = y_train.isin(top_classes)
X_train = X_train[mask_train]
y_train = y_train[mask_train]

mask_test = y_test.isin(top_classes)
X_test = X_test[mask_test]
y_test = y_test[mask_test]

print("--- 1. VERIFY CLASS FILTERING ---")
print("Unique classes:", len(set(y_train)))

print("\n--- 2. VERIFY TRAIN / TEST CONSISTENCY ---")
missing_classes = set(y_test) - set(y_train)
print("Missing classes in test:", missing_classes)

print("\n--- 3. VERIFY LABEL ENCODING (CRITICAL) ---")
le = LabelEncoder()
y_train_enc = pd.Series(le.fit_transform(y_train), index=y_train.index)
y_test_enc = pd.Series(le.transform(y_test), index=y_test.index)
print("Encoded classes:", list(le.classes_)[:10])

print("\n--- 4. VERIFY DATA SIZE ---")
print("Train size:", len(X_train))
print("Test size:", len(X_test))

print("\n--- 5. VERIFY FEATURE ALIGNMENT ---")
if list(X_train.columns) == list(X_test.columns):
    print("Feature alignment: SUCCESS")
else:
    print("Feature alignment: FAILED")

print("\n--- 6. VERIFY CLASS DISTRIBUTION ---")
print(y_train.value_counts().head())

print("\n--- 7-11. VERIFY JSON OUTPUT & METRICS ---")
if REPORT_PATH.exists():
    with open(REPORT_PATH, 'r') as f:
        report = json.load(f)
    
    # 7. VERIFY MODEL OUTPUT (Assuming accuracy > 0 implies valid model)
    # We can't easily print y_pred without running the model, so we check metrics.
    
    # 8. VERIFY ACCURACY IS VALID
    print("model_a accuracy:", report.get("model_a", {}).get("accuracy"))
    print("model_a topk_accuracy:", report.get("model_a", {}).get("topk_accuracy"))
    print("model_b accuracy:", report.get("model_b", {}).get("accuracy"))
    print("model_b topk_accuracy:", report.get("model_b", {}).get("topk_accuracy"))
    
    # 9. VERIFY FAIRNESS METRICS
    print("Gender metrics:", list(report.get("gender_metrics", {}).keys()))
    print("Age metrics:", list(report.get("age_metrics", {}).keys()))
    
    # 10. VERIFY BIAS DETECTION
    print("Bias flag:", report.get("bias_flag"))
    print("Bias details:", report.get("bias_details"))
else:
    print("Report JSON not found.")

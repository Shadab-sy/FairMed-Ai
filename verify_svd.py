import pandas as pd
import numpy as np
import json
import os
from collections import Counter
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import StandardScaler

DATA_DIR = os.path.join("backend", "data", "processed")

# LOAD DATA
X_train = pd.read_csv(os.path.join(DATA_DIR, "fair_X_train.csv"))
X_train = X_train.apply(pd.to_numeric, errors='coerce').fillna(0)
y_train = pd.read_csv(os.path.join(DATA_DIR, "y_train_labels.csv")).squeeze("columns")

# REPLICATE PIPELINE FILTERING
top_classes = y_train.value_counts().head(50).index

mask_train = y_train.isin(top_classes)
X_train = X_train[mask_train]
y_train = y_train[mask_train]

svd_full = TruncatedSVD(n_components=50, random_state=42)
X_train_svd = svd_full.fit_transform(X_train)

scaler_full = StandardScaler()
X_train_svd = scaler_full.fit_transform(X_train_svd)

print("--- 1. VERIFY TRANSFORM SHAPES ---")
print("Original shape:", X_train.shape)
print("SVD shape:", X_train_svd.shape)

print("\n--- 2. VERIFY DENSITY / VARIANCE ---")
print("Mean variance (SVD):", np.mean(np.var(X_train_svd, axis=0)))

print("\n--- 3-6. VERIFY METRICS FROM REPORT ---")
report_path = os.path.join("backend", "models", "model_evaluation_report.json")
try:
    with open(report_path, "r") as f:
        report = json.load(f)
        
    model_b = report.get("model_b", {})
    y_pred = model_b.get("top1", [])
    
    print("Unique predictions:", set(y_pred))
    print("Prediction distribution:", dict(Counter(y_pred)))
    print("Accuracy:", model_b.get("accuracy", 0))
    print("Top-3 Accuracy:", model_b.get("topk_accuracy", 0))
    
    gender = report.get("gender_metrics", {})
    age = report.get("age_metrics", {})
    print("Gender metrics keys:", list(gender.keys()))
    print("Age metrics keys:", list(age.keys()))
except Exception as e:
    print("Failed to read report:", e)

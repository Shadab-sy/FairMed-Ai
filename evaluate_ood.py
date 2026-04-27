import pandas as pd
import numpy as np
import os
from sklearn.model_selection import train_test_split
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import StandardScaler, LabelEncoder
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score

DATA_DIR = os.path.join("backend", "data", "processed")

print("Loading internal data...")
X_full = pd.read_csv(os.path.join(DATA_DIR, "fair_X_train.csv"))
X_full = X_full.apply(pd.to_numeric, errors='coerce').fillna(0)
y_full = pd.read_csv(os.path.join(DATA_DIR, "y_train_labels.csv")).squeeze("columns")

# Filter Top 50
top_classes = y_full.value_counts().head(50).index
mask = y_full.isin(top_classes)
X_full = X_full[mask]
y_full = y_full[mask]

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X_full, y_full, test_size=0.2, stratify=y_full, random_state=42
)

# Label Encoding
le = LabelEncoder()
y_train_enc = le.fit_transform(y_train)
y_test_enc = le.transform(y_test)

# SVD and Scaler
print("Fitting transformations...")
svd = TruncatedSVD(n_components=50, random_state=42)
X_train_svd = svd.fit_transform(X_train)
X_test_svd = svd.transform(X_test)

scaler = StandardScaler()
X_train_svd = scaler.fit_transform(X_train_svd)
X_test_svd = scaler.transform(X_test_svd)

# Train XGBoost
print("Training model...")
X_train_split, X_val, y_train_split, y_val = train_test_split(X_train_svd, y_train_enc, test_size=0.2, random_state=42)
xgb = XGBClassifier(
    use_label_encoder=False, 
    eval_metric='mlogloss', 
    random_state=42, 
    n_estimators=200, 
    max_depth=8, 
    learning_rate=0.1,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_lambda=1,
    reg_alpha=0.5,
    verbosity=0, 
    early_stopping_rounds=20,
    n_jobs=-1
)
xgb.fit(X_train_split, y_train_split, eval_set=[(X_val, y_val)], verbose=False)

# Internal Eval
internal_probs = xgb.predict_proba(X_test_svd)
internal_preds = np.argmax(internal_probs, axis=1)
internal_acc = accuracy_score(y_test_enc, internal_preds)

top_k_correct = (np.argsort(internal_probs, axis=1)[:, -3:] == y_test_enc[:, None]).any(axis=1)
internal_top3 = np.mean(top_k_correct)

print(f"\n--- INTERNAL TEST METRICS ---")
print(f"Accuracy: {internal_acc:.4f}")
print(f"Top-3 Accuracy: {internal_top3:.4f}")

# --- OUT OF DISTRIBUTION EVAL ---
print("\nLoading OOD data...")
X_ood = pd.read_csv(os.path.join(DATA_DIR, "fair_X_test_patient.csv"))
X_ood = X_ood.apply(pd.to_numeric, errors='coerce').fillna(0)
y_ood = pd.read_csv(os.path.join(DATA_DIR, "fair_y_test_patient.csv")).squeeze("columns")

# Filter Top 50 (if any present)
mask_ood = y_ood.isin(top_classes)
X_ood = X_ood[mask_ood]
y_ood = y_ood[mask_ood]
y_ood_enc = le.transform(y_ood)

# Align columns
for col in X_train.columns:
    if col not in X_ood.columns:
        X_ood[col] = 0
X_ood = X_ood[X_train.columns]

# Transform
X_ood_svd = svd.transform(X_ood)
X_ood_svd = scaler.transform(X_ood_svd)

# Predict
ood_probs = xgb.predict_proba(X_ood_svd)
ood_preds = np.argmax(ood_probs, axis=1)

ood_acc = accuracy_score(y_ood_enc, ood_preds)
ood_top_k_correct = (np.argsort(ood_probs, axis=1)[:, -3:] == y_ood_enc[:, None]).any(axis=1)
ood_top3 = np.mean(ood_top_k_correct)

print(f"\n--- OOD TEST METRICS ---")
print(f"OOD Samples: {len(y_ood)}")
print(f"Accuracy: {ood_acc:.4f}")
print(f"Top-3 Accuracy: {ood_top3:.4f}")

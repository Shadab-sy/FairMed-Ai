import pandas as pd
import numpy as np
import os
from sklearn.model_selection import train_test_split
from imblearn.over_sampling import RandomOverSampler
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import StandardScaler, LabelEncoder
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score

DATA_DIR = os.path.join("backend", "data", "processed")

# 1. LOAD RAW DATA ONLY
print("Loading real data...")
X_real = pd.read_csv(os.path.join(DATA_DIR, "fair_X_test_patient.csv"))
X_real = X_real.apply(pd.to_numeric, errors='coerce').fillna(0)
y_real = pd.read_csv(os.path.join(DATA_DIR, "fair_y_test_patient.csv")).squeeze("columns")

# Filter classes with at least 2 samples so stratify works
counts = y_real.value_counts()
valid_classes = counts[counts >= 2].index
mask = y_real.isin(valid_classes)
X_real = X_real[mask]
y_real = y_real[mask]

# 2. APPLY TRAIN-TEST SPLIT FIRST
print("Splitting data...")
X_train_real, X_val_real, y_train_real, y_val_real = train_test_split(
    X_real,
    y_real,
    test_size=0.2,
    stratify=y_real,
    random_state=42
)

# --------------------------------
# 1. REDUCE CLASS COMPLEXITY
# --------------------------------
top_classes = y_train_real.value_counts().head(15).index

mask_train = y_train_real.isin(top_classes)
mask_val = y_val_real.isin(top_classes)

X_train_real = X_train_real[mask_train].copy()
y_train_real = y_train_real[mask_train].copy()

X_val_real = X_val_real[mask_val].copy()
y_val_real = y_val_real[mask_val].copy()

# Label Encoding
le = LabelEncoder()
y_train_real_enc = le.fit_transform(y_train_real)
y_val_real_enc = le.transform(y_val_real)

# --------------------------------
# 3. ADD FEATURE ENGINEERING
# --------------------------------
X_train_real["symptom_count"] = X_train_real.sum(axis=1)
X_val_real["symptom_count"] = X_val_real.sum(axis=1)

# --------------------------------
# 2. APPLY AUGMENTATION (TRAIN ONLY)
# --------------------------------
print("Augmenting training data...")
ros = RandomOverSampler(random_state=42)
X_train_aug, y_train_aug_enc = ros.fit_resample(X_train_real, y_train_real_enc)

# --------------------------------
# 4. APPLY SVD + SCALING (CORRECT ORDER)
# --------------------------------
print("Fitting SVD and Scaler...")
svd = TruncatedSVD(n_components=50, random_state=42)
# Fit ONLY on X_train_real
X_train_svd = svd.fit_transform(X_train_real)
X_val_svd = svd.transform(X_val_real)
X_train_aug_svd = svd.transform(X_train_aug)

scaler = StandardScaler()
X_train_svd = scaler.fit_transform(X_train_svd)
X_val_svd = scaler.transform(X_val_svd)
X_train_aug_svd = scaler.transform(X_train_aug_svd)

# --------------------------------
# 5. TRAIN MODEL
# --------------------------------
print("Training model...")
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
    n_jobs=-1
)
# Train ONLY on augmented training data
xgb.fit(X_train_aug_svd, y_train_aug_enc, verbose=False)

# --------------------------------
# 6. EVALUATE WITH TOP-K METRICS
# --------------------------------
print("Evaluating model...")
val_probs = xgb.predict_proba(X_val_svd)
val_preds = np.argmax(val_probs, axis=1)

final_accuracy = accuracy_score(y_val_real_enc, val_preds)

top_3_correct = (np.argsort(val_probs, axis=1)[:, -3:] == y_val_real_enc[:, None]).any(axis=1)
top_3_acc = np.mean(top_3_correct)

top_5_correct = (np.argsort(val_probs, axis=1)[:, -5:] == y_val_real_enc[:, None]).any(axis=1)
top_5_acc = np.mean(top_5_correct)

print(f"\n--- VALIDATION METRICS ---")
print(f"Validation Samples: {len(y_val_real_enc)}")
print(f"Final Accuracy: {final_accuracy:.4f}")
print(f"Top-3 Accuracy: {top_3_acc:.4f}")
print(f"Top-5 Accuracy: {top_5_acc:.4f}")

# --------------------------------
# 7. ADD CONFIDENCE THRESHOLD
# --------------------------------
max_probs = np.max(val_probs, axis=1)

best_threshold = 0.0
best_guarded_acc = 0.0
print("\n--- THRESHOLD ANALYSIS ---")
for t in [0.3, 0.4, 0.5, 0.6]:
    guarded_preds = np.where(max_probs < t, -1, val_preds)
    
    known_mask = guarded_preds != -1
    if np.any(known_mask):
        acc = accuracy_score(y_val_real_enc[known_mask], guarded_preds[known_mask])
    else:
        acc = 0.0
        
    pct_unknown = np.mean(guarded_preds == -1) * 100
    
    print(f"Threshold {t}:")
    print(f"  Accuracy (excluding UNKNOWN): {acc:.4f}")
    print(f"  % UNKNOWN predictions: {pct_unknown:.2f}%")
    
    if acc > best_guarded_acc:
        best_guarded_acc = acc
        best_threshold = t

# --------------------------------
# 8. REPORT RESULTS
# --------------------------------
print(f"\n--- FINAL RESULTS ---")
print(f"Final Accuracy: {final_accuracy:.4f}")
print(f"Top-3 Accuracy: {top_3_acc:.4f}")
print(f"Top-5 Accuracy: {top_5_acc:.4f}")
best_pct_unknown = np.mean((np.where(max_probs < best_threshold, -1, val_preds)) == -1) * 100
print(f"% UNKNOWN predictions at best threshold ({best_threshold}): {best_pct_unknown:.2f}%")
print(f"Best threshold value: {best_threshold}")

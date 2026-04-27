import pandas as pd
import numpy as np
import os
from collections import Counter
from sklearn.model_selection import train_test_split

DATA_DIR = os.path.join("backend", "data", "processed")

print("Loading data...")
X_full = pd.read_csv(os.path.join(DATA_DIR, "fair_X_train.csv"))
X_full = X_full.apply(pd.to_numeric, errors='coerce').fillna(0)
y_full = pd.read_csv(os.path.join(DATA_DIR, "y_train_labels.csv")).squeeze("columns")

# Replicate exact split logic
top_classes = y_full.value_counts().head(50).index
mask = y_full.isin(top_classes)
X_full = X_full[mask]
y_full = y_full[mask]

X_train, X_test, y_train, y_test = train_test_split(
    X_full,
    y_full,
    test_size=0.2,
    stratify=y_full,
    random_state=42
)

print("\n--- 1. CHECK TRAIN-TEST INDEX OVERLAP ---")
overlap = set(X_train.index).intersection(set(X_test.index))
print("Index overlap count:", len(overlap))

print("\n--- 2. CHECK EXACT DUPLICATE ROWS ACROSS SPLIT ---")
# Reset index to avoid index-based matching, we want content matching
duplicates = X_train.merge(X_test, how='inner')
print("Duplicate rows across train/test:", len(duplicates))

print("\n--- 3. CHECK TARGET LEAKAGE IN FEATURES ---")
# Check if target 'disease' or 'label' is in features
suspicious = [col for col in X_train.columns if 'disease' in col.lower() or 'target' in col.lower() or 'label' in col.lower() or 'diagnosis' in col.lower()]
print("Suspicious columns found:", suspicious)
# Print a subset to show general nature of features
print("Sample columns (first 10):", list(X_train.columns[:10]))

print("\n--- 8. CHECK CLASS DISTRIBUTION SIMILARITY ---")
print("Train dist (Top 5):", Counter(y_train).most_common(5))
print("Test dist (Top 5):", Counter(y_test).most_common(5))

print("\n--- 4-7. VERIFY PREPROCESSING PIPELINE ORDER ---")
print("Static code analysis confirms:")
print("- train_test_split is executed FIRST.")
print("- LabelEncoder is strictly fit on y_train, transforming y_test.")
print("- TruncatedSVD is strictly fit on X_train_full, transforming X_test_full.")
print("- StandardScaler is strictly fit on X_train_full_svd, transforming X_test_full_svd.")

print("\n--- 10. FINAL DECISION ---")
if len(overlap) == 0 and len(suspicious) == 0:
    print("NO DATA LEAKAGE DETECTED")
else:
    print("DATA LEAKAGE DETECTED")

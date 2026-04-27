import pandas as pd
import numpy as np
from collections import Counter
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
import os

DATA_DIR = os.path.join("backend", "data", "processed")

# LOAD DATA
X_train = pd.read_csv(os.path.join(DATA_DIR, "fair_X_train.csv"))
X_train = X_train.apply(pd.to_numeric, errors='coerce').fillna(0)
y_train = pd.read_csv(os.path.join(DATA_DIR, "y_train_labels.csv")).squeeze("columns")

X_test = pd.read_csv(os.path.join(DATA_DIR, "fair_X_test_patient.csv"))
X_test = X_test.apply(pd.to_numeric, errors='coerce').fillna(0)
y_test = pd.read_csv(os.path.join(DATA_DIR, "fair_y_test_patient.csv")).squeeze("columns")

# REPLICATE PIPELINE FILTERING
top_classes = y_train.value_counts().head(50).index

mask_train = y_train.isin(top_classes)
X_train = X_train[mask_train]
y_train = y_train[mask_train]

mask_test = y_test.isin(top_classes)
X_test = X_test[mask_test]
y_test = y_test[mask_test]

# FEATURE ALIGNMENT
X_test = X_test[X_train.columns]

# LABEL ENCODING
le = LabelEncoder()
y_train = pd.Series(le.fit_transform(y_train), index=y_train.index)
y_test = pd.Series(le.transform(y_test), index=y_test.index)

print("\n--- 1. VERIFY LABEL PIPELINE ---")
unique_train = set(y_train)
unique_test = set(y_test)
print("Unique y_train count:", len(unique_train))
print("Unique y_test count:", len(unique_test))
print("y_train range:", min(unique_train), "to", max(unique_train))

print("\n--- 2. CHECK CLASS DISTRIBUTION ---")
print("Train dist:", Counter(y_train).most_common(5))
print("Test dist:", Counter(y_test))

print("\n--- 3. CHECK FEATURE VARIANCE ---")
print("Non-zero avg:", (X_train != 0).sum(axis=1).mean())
print("Feature variance:", X_train.var().mean())

print("\n--- 4. CHECK IDENTICAL ROWS ---")
duplicates = X_train.duplicated().sum()
print("Duplicate rows:", duplicates)

print("\n--- 5. CHECK SAMPLE INPUTS ---")
sample_row = X_train.iloc[0]
print("Sample row non-zero values:", sample_row[sample_row != 0].to_dict())
print("Non-zero features:", np.count_nonzero(sample_row))

print("\n--- 6. CHECK MODEL INPUT SHAPE ---")
print("Shape:", X_train.shape)

print("\n--- 7. TEST SIMPLE MODEL (IMPORTANT) ---")
lr = LogisticRegression(max_iter=100) # Fast, no tuning
lr.fit(X_train, y_train)
lr_preds = lr.predict(X_test)
print("Logistic Regression predictions:", set(lr_preds))
print("Logistic Regression Accuracy:", accuracy_score(y_test, lr_preds))

print("\n--- 8. SHUFFLE TEST ---")
np.random.seed(42)
X_test_shuffled = X_test.copy()
# Shuffle rows
indices = np.arange(len(X_test_shuffled))
np.random.shuffle(indices)
X_test_shuffled = X_test_shuffled.iloc[indices]

lr_shuffled_preds = lr.predict(X_test_shuffled)
print("Logistic Regression predictions (Shuffled X_test):", set(lr_shuffled_preds))

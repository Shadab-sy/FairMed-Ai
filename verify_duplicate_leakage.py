import pandas as pd
import os
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

# 1. FIND EXACT DUPLICATES WITH LABELS
train_df = X_train.copy()
train_df["target"] = y_train

test_df = X_test.copy()
test_df["target"] = y_test

# Find exact matching features across train and test
duplicates = train_df.merge(test_df, on=list(X_train.columns))

# 2. CHECK LABEL MATCHING
same_label = duplicates[duplicates["target_x"] == duplicates["target_y"]]
print("Duplicates with same label (Leakage):", len(same_label))

# 3. CHECK DIFFERENT LABEL CASES
diff_label = duplicates[duplicates["target_x"] != duplicates["target_y"]]
print("Duplicates with different labels (Inconsistency):", len(diff_label))

print("Total exact duplicates between train/test:", len(duplicates))

"""
Disease prediction and fairness evaluation pipeline.

Produces model_evaluation_report.json

Requirements:
- sklearn
- xgboost
- pandas
- numpy

Run:
python backend/scripts/fairness_pipeline.py
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.utils.class_weight import compute_class_weight
from sklearn.preprocessing import LabelBinarizer
from xgboost import XGBClassifier
import warnings
warnings.filterwarnings("ignore")

# Reproducibility
RANDOM_STATE = 42

# Paths
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
REPORT_PATH = ROOT / "models" / "model_evaluation_report.json"

PROTECTED = ["age", "gender_female", "gender_male"]


def load_data():
    X_train = pd.read_csv(DATA_DIR / "fair_X_train.csv")
    y_train = pd.read_csv(DATA_DIR / "y_train_labels.csv")
    X_ood = pd.read_csv(DATA_DIR / "fair_X_test_patient.csv")
    y_ood = pd.read_csv(DATA_DIR / "fair_y_test_patient.csv")
    with open(DATA_DIR / "preprocessing_metadata.json", "r", encoding="utf-8") as f:
        meta = json.load(f)

    # Ensure y are 1d arrays
    if y_train.shape[1] == 1:
        y_train = y_train.iloc[:,0]
    if y_ood.shape[1] == 1:
        y_ood = y_ood.iloc[:,0]

    # Align columns: keep intersection and warn if mismatch
    train_cols = list(X_train.columns)
    ood_cols = list(X_ood.columns)
    missing_cols = set(train_cols) - set(ood_cols)
    if missing_cols:
        raise ValueError(f"Critical mismatch: Missing columns in OOD set: {missing_cols}")
        
    if train_cols != ood_cols:
        # reorder OOD to train order
        X_ood = X_ood[train_cols]

    return X_train, y_train, X_ood, y_ood, meta


def compute_class_weights(y):
    classes = np.unique(y)
    class_weights = compute_class_weight(class_weight='balanced', classes=classes, y=y)
    return dict(zip(classes, class_weights))


def split_features(X, protected=PROTECTED):
    base = X.drop(columns=[c for c in protected if c in X.columns])
    full = X.copy()
    return base, full


def get_topk_preds_from_model(model, X, k=3):
    proba = model.predict_proba(X)
    # model.classes_ holds class labels
    classes = model.classes_
    top1_idx = np.argmax(proba, axis=1)
    top1 = classes[top1_idx]
    topk_idx = np.argsort(proba, axis=1)[:, ::-1][:, :k]
    topk = classes[topk_idx]
    return proba, np.array(top1), topk


def macro_fpr_fnr_from_confusion(cm):
    # cm is confusion matrix for multiclass: shape (n_classes, n_classes)
    # For each class i: TP = cm[i,i], FN = sum(cm[i,:]) - TP, FP = sum(cm[:,i]) - TP, TN = total - TP - FP - FN
    n = cm.sum()
    n_classes = cm.shape[0]
    fpr_list = []
    fnr_list = []
    for i in range(n_classes):
        TP = cm[i, i]
        FN = cm[i, :].sum() - TP
        FP = cm[:, i].sum() - TP
        TN = n - TP - FP - FN
        fpr = FP / (FP + TN) if (FP + TN) > 0 else 0.0
        fnr = FN / (FN + TP) if (FN + TP) > 0 else 0.0
        fpr_list.append(fpr)
        fnr_list.append(fnr)
    return float(np.mean(fpr_list)), float(np.mean(fnr_list))


def evaluate_model(model, X_test, y_test, topk=3):
    proba, top1, topk_preds = get_topk_preds_from_model(model, X_test, k=topk)
    acc = accuracy_score(y_test, top1)
    # top-k accuracy
    y_true_arr = y_test.values if hasattr(y_test, 'values') else np.array(y_test)
    topk_correct = (topk_preds == y_true_arr[:, None]).any(axis=1)
    topk_acc = float(np.mean(topk_correct))
    cm = confusion_matrix(y_test, top1, labels=model.classes_)
    macro_fpr, macro_fnr = macro_fpr_fnr_from_confusion(cm)
    # Per sample FPR/FNR for Top-1: compute FP and FN per class then macro average
    return dict(
        accuracy=float(acc),
        topk_accuracy=float(topk_acc),
        confusion_matrix=cm.tolist(),
        proba=proba.tolist(),
        top1=top1.tolist(),
        topk=topk_preds.tolist(),
        macro_fpr=macro_fpr,
        macro_fnr=macro_fnr,
    )


def fairness_by_gender(X_test, y_test, top1_preds, classes):
    results = {}
    from sklearn.metrics import confusion_matrix, recall_score
    for gender_col, label in [("gender_male", "male"), ("gender_female", "female")]:
        if gender_col not in X_test.columns:
            continue
        mask = X_test[gender_col] == 1
        if mask.sum() == 0:
            results[gender_col] = None
            continue
        y_t = y_test[mask]
        y_p = pd.Series(top1_preds, index=X_test.index)[mask]
        acc = accuracy_score(y_t, y_p)
        recall = recall_score(y_t, y_p, average='macro', zero_division=0)
        # compute FPR/FNR per group (Top-1)
        cm = confusion_matrix(y_t, y_p, labels=classes)
        fpr, fnr = macro_fpr_fnr_from_confusion(cm)
        results[gender_col] = dict(accuracy=float(acc), recall=float(recall), fpr=fpr, fnr=fnr, n=int(mask.sum()))
    return results


def fairness_by_age_groups(X_test, y_test, top1_preds, classes):
    age = X_test["age"] if "age" in X_test.columns else None
    groups = {
        "0-18": (0, 18),
        "19-40": (19, 40),
        "41-60": (41, 60),
        "60+": (61, 200),
    }
    results = {}
    from sklearn.metrics import recall_score, confusion_matrix
    for name, (lo, hi) in groups.items():
        if age is None:
            results[name] = None
            continue
        mask = (age >= lo) & (age <= hi)
        if mask.sum() == 0:
            results[name] = None
            continue
        y_t = y_test[mask]
        y_p = pd.Series(top1_preds, index=X_test.index)[mask]
        acc = accuracy_score(y_t, y_p)
        recall = recall_score(y_t, y_p, average='macro', zero_division=0)
        cm = confusion_matrix(y_t, y_p, labels=classes)
        fpr, fnr = macro_fpr_fnr_from_confusion(cm)
        results[name] = dict(accuracy=float(acc), recall=float(recall), fpr=fpr, fnr=fnr, n=int(mask.sum()))
    return results


def main():
    X_train_orig, y_train_orig, X_ood_raw, y_ood_raw, meta = load_data()

    # FILTER TOP FREQUENT DISEASES
    top_classes = y_train_orig.value_counts().head(50).index
    
    mask = y_train_orig.isin(top_classes)
    X_full = X_train_orig[mask]
    y_full = y_train_orig[mask]
    
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X_full,
        y_full,
        test_size=0.2,
        stratify=y_full,
        random_state=42
    )
    
    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder()
    y_train = pd.Series(le.fit_transform(y_train), index=y_train.index)
    y_test = pd.Series(le.transform(y_test), index=y_test.index)

    # ── OOD PREP (fixed) ──────────────────────────────────────────────
    # y_ood_raw contains raw integer codes from preprocess.py
    # le was also fitted on those same integer codes
    # So match directly on integer codes — no decoding needed

    ood_known_mask = y_ood_raw.isin(top_classes)
    X_ood = X_ood_raw[ood_known_mask].reset_index(drop=True)
    y_ood_filtered = y_ood_raw[ood_known_mask].reset_index(drop=True)

    # Only keep labels le actually knows
    le_known_mask = y_ood_filtered.isin(le.classes_)
    X_ood = X_ood[le_known_mask].reset_index(drop=True)
    y_ood_filtered = y_ood_filtered[le_known_mask].reset_index(drop=True)
    y_ood = pd.Series(le.transform(y_ood_filtered), name='label')

    print(f"OOD samples after correct label mapping: {len(X_ood)}")
    print(f"OOD unique disease codes: {y_ood_filtered.unique()}")
    # ── END OOD PREP ──────────────────────────────────────────────────

    train_cols = X_train.columns.tolist()
    for col in train_cols:
        if col not in X_ood.columns:
            X_ood[col] = 0
    X_ood = X_ood[train_cols].reset_index(drop=True)
    X_ood = X_ood.apply(pd.to_numeric, errors='coerce').fillna(0)
    print(f"OOD samples available: {len(X_ood)}")
    
    print("\n=== OOD DIAGNOSTIC ===")
    if len(y_ood_filtered) > 0:
        print("OOD label distribution:\n", y_ood_filtered.value_counts())
    print("OOD feature mean (first 5):", X_ood.iloc[:, :5].mean().values if len(X_ood) > 0 else "N/A")
    print("Train feature mean (first 5):", X_train.iloc[:, :5].mean().values)
    if len(X_ood) > 0:
        print("OOD non-zero features per row (avg):", (X_ood > 0).sum(axis=1).mean())
    print("Train non-zero features per row (avg):", (X_train > 0).sum(axis=1).mean())
    print("======================\n")
    
    print(f"Number of classes used: {len(top_classes)}")
    print(f"Number of training samples: {len(y_train)}")
    print(f"Number of test samples: {len(y_test)}")

    if len(X_train) > 20000:
        print("Sampling training data for faster execution...")

        idx_per_class = y_train.groupby(y_train).head(1).index
        remaining = 20000 - len(idx_per_class)

        if remaining > 0:
            remaining_idx = X_train.drop(index=idx_per_class).sample(
                n=remaining,
                random_state=42
            ).index
            sample_idx = idx_per_class.union(remaining_idx)
        else:
            sample_idx = idx_per_class

        X_train = X_train.loc[sample_idx]
        y_train = y_train.loc[sample_idx]

    # compute class weights
    class_weights = compute_class_weights(y_train)

    # Encode categorical (non-numeric) columns using get_dummies on combined data to
    # ensure train/test columns align. This preserves all categories (no dropping).
    combined = pd.concat([X_train, X_test], axis=0).reset_index(drop=True)
    # create partition marker after detecting object cols
    obj_cols = combined.select_dtypes(include=['object', 'category']).columns.tolist()
    if len(obj_cols) > 0:
        # mark partitions then get dummies excluding the partition column
        part = ['train'] * len(X_train) + ['test'] * len(X_test)
        combined['_part'] = part
        combined = pd.get_dummies(combined.drop(columns=['_part']), columns=obj_cols, drop_first=False)
        combined['_part'] = part
        X_train = combined[combined['_part']=='train'].drop(columns=['_part']).reset_index(drop=True)
        X_test = combined[combined['_part']=='test'].drop(columns=['_part']).reset_index(drop=True)
    else:
        # ensure indices are simple
        X_train = X_train.reset_index(drop=True)
        X_test = X_test.reset_index(drop=True)

    # feature splits
    X_train_base, X_train_full = split_features(X_train)
    X_test_base, X_test_full = split_features(X_test)

    # Model A: RandomForest on base features (smaller/safer config to avoid OOM)
    from sklearn.decomposition import TruncatedSVD
    from sklearn.preprocessing import StandardScaler

    svd_base = TruncatedSVD(n_components=50, random_state=42)
    X_train_base_svd = svd_base.fit_transform(X_train_base)
    X_test_base_svd = svd_base.transform(X_test_base)
    
    scaler_base = StandardScaler()
    X_train_base_svd = scaler_base.fit_transform(X_train_base_svd)
    X_test_base_svd = scaler_base.transform(X_test_base_svd)

    rf = RandomForestClassifier(random_state=RANDOM_STATE, n_estimators=20, max_depth=10, n_jobs=-1)
    try:
        rf.fit(X_train_base_svd, y_train)
    except MemoryError:
        # fallback to smaller model
        rf = RandomForestClassifier(random_state=RANDOM_STATE, n_estimators=20, max_depth=8, n_jobs=-1)
        rf.fit(X_train_base_svd, y_train)
    rf_eval = evaluate_model(rf, X_test_base_svd, y_test, topk=3)

    # Model B: XGBoost on full features
    svd_full = TruncatedSVD(n_components=50, random_state=42)
    X_train_full_svd = svd_full.fit_transform(X_train_full)
    X_test_full_svd = svd_full.transform(X_test_full)
    
    scaler_full = StandardScaler()
    X_train_full_svd = scaler_full.fit_transform(X_train_full_svd)
    X_test_full_svd = scaler_full.transform(X_test_full_svd)

    from sklearn.model_selection import train_test_split
    X_train_split, X_val, y_train_split, y_val = train_test_split(X_train_full_svd, y_train, test_size=0.2, random_state=42)
    
    xgb = XGBClassifier(
        use_label_encoder=False, 
        eval_metric='mlogloss', 
        random_state=RANDOM_STATE, 
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
    xgb.fit(
        X_train_split, y_train_split,
        eval_set=[(X_val, y_val)],
        verbose=False
    )
    xgb_eval = evaluate_model(xgb, X_test_full_svd, y_test, topk=3)

    from collections import Counter
    print("Unique predictions:", set(xgb_eval['top1']))
    print("Prediction counts:", Counter(xgb_eval['top1']))
    print("Accuracy:", xgb_eval['accuracy'])
    print("Top-3 Accuracy:", xgb_eval['topk_accuracy'])

    assert hasattr(xgb, 'feature_importances_'), "Model not trained yet!"
    if len(X_ood) == 0:
        print("WARNING: No OOD samples matched training classes. Skipping OOD eval.")
        xgb_ood_eval = {"accuracy": 0.0, "topk_accuracy": 0.0}
    else:
        _, X_ood_full = split_features(X_ood)
        X_ood_full_svd = svd_full.transform(X_ood_full)       # transform only, never fit
        X_ood_full_svd = scaler_full.transform(X_ood_full_svd) # transform only, never fit
        xgb_ood_eval = evaluate_model(xgb, X_ood_full_svd, y_ood, topk=3)
        print(f"\n=== OOD VALIDATION (Real Patients) ===")
        print(f"OOD Samples:    {len(X_ood)}")
        print(f"OOD Accuracy:   {xgb_ood_eval['accuracy']:.2%}")
        print(f"OOD Top-3 Acc:  {xgb_ood_eval['topk_accuracy']:.2%}\n")

    # Fairness (Model B)
    xgb_top1 = np.array(xgb_eval['top1'])
    xgb_classes = xgb.classes_
    gender_metrics = fairness_by_gender(X_test_full, y_test.reset_index(drop=True), xgb_top1, xgb_classes)
    age_metrics = fairness_by_age_groups(X_test_full, y_test.reset_index(drop=True), xgb_top1, xgb_classes)
    

    # Bias detection
    bias_details = {}
    bias_detected = False
    
    # Gender bias detection
    m_res = gender_metrics.get("gender_male")
    f_res = gender_metrics.get("gender_female")
    if m_res and f_res:
        for metric in ["accuracy", "recall", "fpr", "fnr"]:
            diff = abs(m_res[metric] - f_res[metric])
            if diff > 0.1:
                bias_detected = True
                bias_details[f"Gender_{metric}"] = f"BIAS DETECTED (Difference: {diff:.2%})"

    # Age bias detection
    valid_age_res = {k: v for k, v in age_metrics.items() if v is not None}
    if valid_age_res:
        for metric in ["accuracy", "recall", "fpr", "fnr"]:
            vals = [res[metric] for res in valid_age_res.values()]
            if vals and (max(vals) - min(vals) > 0.1):
                bias_detected = True
                bias_details[f"Age_{metric}"] = f"BIAS DETECTED (Max Difference: {max(vals) - min(vals):.2%})"
                
    if not bias_details:
        bias_details["Status"] = "All metric differences <= 10%"

    bias_flag = "BIAS DETECTED" if bias_detected else "NO SIGNIFICANT BIAS"

    # Model comparison
    comparison = {
        "Accuracy_Diff": abs(xgb_eval['accuracy'] - rf_eval['accuracy']),
        "Top_3_Accuracy_Diff": abs(xgb_eval['topk_accuracy'] - rf_eval['topk_accuracy'])
    }
    recommended = "model_b" if xgb_eval['accuracy'] >= rf_eval['accuracy'] else "model_a"

    report = {
        "model_a": rf_eval,
        "model_b": xgb_eval,
        "ood_validation": {
            "samples": len(X_ood),
            "accuracy": xgb_ood_eval['accuracy'],
            "top3_accuracy": xgb_ood_eval['topk_accuracy'],
        },
        "gender_metrics": gender_metrics,
        "age_metrics": age_metrics,
        "macro_fpr": xgb_eval['macro_fpr'],
        "macro_fnr": xgb_eval['macro_fnr'],
        "bias_flag": bias_flag,
        "bias_details": bias_details,
        "model_comparison": comparison,
        "recommended_model": recommended
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Print summary to console
    print("Model A (RandomForest) Accuracy:", rf_eval['accuracy'])
    print("Model B (XGBoost) Accuracy:", xgb_eval['accuracy'])
    print("Bias flag:", bias_flag)
    print("Report saved to", REPORT_PATH)


if __name__ == '__main__':
    main()

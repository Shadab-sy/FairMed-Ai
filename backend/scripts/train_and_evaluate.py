import pandas as pd
import numpy as np
import json
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, recall_score
from sklearn.utils.class_weight import compute_class_weight
import xgboost as xgb

def calculate_top_k_accuracy(y_true, y_probs, classes, k=3):
    top_k_indices = np.argsort(y_probs, axis=1)[:, -k:]
    top_k_preds = classes[top_k_indices]
    
    y_true_arr = y_true.values if isinstance(y_true, pd.Series) else np.array(y_true)
    
    top_k_correct = (top_k_preds == y_true_arr[:, None]).any(axis=1)
    return float(np.mean(top_k_correct))

def get_fpr_fnr(y_true, y_pred, classes):
    cm = confusion_matrix(y_true, y_pred, labels=classes)
    fp = cm.sum(axis=0) - np.diag(cm)
    fn = cm.sum(axis=1) - np.diag(cm)
    tp = np.diag(cm)
    tn = cm.sum() - (fp + fn + tp)
    
    fpr = np.divide(fp, fp + tn, out=np.zeros_like(fp, dtype=float), where=(fp + tn) > 0)
    fnr = np.divide(fn, fn + tp, out=np.zeros_like(fn, dtype=float), where=(fn + tp) > 0)
    
    # Macro average
    return np.mean(fpr), np.mean(fnr)

def main():
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "data", "processed")
    MODELS_DIR = os.path.join(BASE_DIR, "models")
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    # 1. LOAD DATA
    print("Loading data...")
    X_full = pd.read_csv(os.path.join(DATA_DIR, "fair_X_train.csv"))
    X_full = X_full.apply(pd.to_numeric, errors='coerce').fillna(0)
    y_full = pd.read_csv(os.path.join(DATA_DIR, "y_train_labels.csv")).squeeze("columns")

    # FILTER TOP FREQUENT DISEASES
    top_classes = y_full.value_counts().head(50).index
    mask = y_full.isin(top_classes)
    X_full = X_full[mask]
    y_full = y_full[mask]

    # TRAIN TEST SPLIT
    from sklearn.model_selection import train_test_split
    X_train_full, X_test_full, y_train, y_test = train_test_split(
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
    print(f"Number of classes used: {len(top_classes)}")
    print(f"Number of training samples: {len(y_train)}")
    print(f"Number of test samples: {len(y_test)}")
    
    with open(os.path.join(DATA_DIR, "preprocessing_metadata.json"), "r") as f:
        metadata = json.load(f)
        
    num_classes = len(top_classes)
    
    # FEATURE ALIGNMENT
    # No longer needed as X_test_full is perfectly aligned from the same dataset
    
    # 2. HANDLE CLASS IMBALANCE
    classes = np.unique(y_train)
    # weights = compute_class_weight(class_weight='balanced', classes=classes, y=y_train)
    # class_weights_dict = {classes[i]: weights[i] for i in range(len(classes))}
    # sample_weights = y_train.map(class_weights_dict).values
    
    # 3. FEATURE SPLIT
    protected_attrs = ['age', 'gender_female', 'gender_male']
    X_train_base = X_train_full.drop(columns=[col for col in protected_attrs if col in X_train_full.columns])
    X_test_base = X_test_full.drop(columns=[col for col in protected_attrs if col in X_test_full.columns])
    
    # Reorder base columns as well
    X_test_base = X_test_base[X_train_base.columns]
    
    # 4. MODEL A (BASELINE)
    print("Training Model A (RandomForest Baseline)...")
    from sklearn.decomposition import TruncatedSVD
    from sklearn.preprocessing import StandardScaler
    
    svd_base = TruncatedSVD(n_components=50, random_state=42)
    X_train_base_svd = svd_base.fit_transform(X_train_base)
    X_test_base_svd = svd_base.transform(X_test_base)
    
    scaler_base = StandardScaler()
    X_train_base_svd = scaler_base.fit_transform(X_train_base_svd)
    X_test_base_svd = scaler_base.transform(X_test_base_svd)

    rf = RandomForestClassifier(random_state=42, n_estimators=20, max_depth=10, n_jobs=-1)
    rf.fit(X_train_base_svd, y_train)
    
    rf_probs = rf.predict_proba(X_test_base_svd)
    rf_preds = rf.classes_[np.argmax(rf_probs, axis=1)]
    
    rf_acc = accuracy_score(y_test, rf_preds)
    rf_top3_acc = calculate_top_k_accuracy(y_test, rf_probs, rf.classes_, k=3)
    
    # 5. MODEL B (MAIN MODEL)
    print("Training Model B (XGBoost)...")
    
    svd_full = TruncatedSVD(n_components=50, random_state=42)
    X_train_full_svd = svd_full.fit_transform(X_train_full)
    X_test_full_svd = svd_full.transform(X_test_full)
    
    scaler_full = StandardScaler()
    X_train_full_svd = scaler_full.fit_transform(X_train_full_svd)
    X_test_full_svd = scaler_full.transform(X_test_full_svd)
    
    from sklearn.model_selection import train_test_split
    X_train_split, X_val, y_train_split, y_val = train_test_split(X_train_full_svd, y_train, test_size=0.2, random_state=42)
    
    xgb_model = xgb.XGBClassifier(
        objective='multi:softprob', 
        num_class=num_classes, 
        n_estimators=200, 
        max_depth=8, 
        learning_rate=0.1, 
        subsample=0.8, 
        colsample_bytree=0.8, 
        reg_lambda=1, 
        reg_alpha=0.5, 
        random_state=42, 
        early_stopping_rounds=20,
        n_jobs=-1
    )
    xgb_model.fit(
        X_train_split, y_train_split, 
        eval_set=[(X_val, y_val)], 
        verbose=False
    )
    
    xgb_probs = xgb_model.predict_proba(X_test_full_svd)
    xgb_preds = xgb_model.classes_[np.argmax(xgb_probs, axis=1)]
    
    from collections import Counter
    print("Unique predictions:", set(xgb_preds))
    print("Prediction counts:", Counter(xgb_preds))
    
    xgb_acc = accuracy_score(y_test, xgb_preds)
    xgb_top3_acc = calculate_top_k_accuracy(y_test, xgb_probs, xgb_model.classes_, k=3)
    
    print("Accuracy:", xgb_acc)
    print("Top-3 Accuracy:", xgb_top3_acc)
    
    # 7. EVALUATION
    model_a_results = {
        "Accuracy": rf_acc,
        "Top_3_Accuracy": rf_top3_acc
    }
    
    model_b_results = {
        "Accuracy": xgb_acc,
        "Top_3_Accuracy": xgb_top3_acc
    }
    
    # 8. FAIRNESS ANALYSIS (MODEL B)
    print("Performing Fairness Analysis...")
    
    # Overall Macro Metrics
    overall_fpr, overall_fnr = get_fpr_fnr(y_test, xgb_preds, xgb_model.classes_)
    
    # Gender subsets
    male_mask = X_test_full['gender_male'] == 1
    female_mask = X_test_full['gender_female'] == 1
    
    def evaluate_subset(mask):
        if not mask.any():
            return None
        y_t = y_test[mask]
        y_p = xgb_preds[mask]
        acc = accuracy_score(y_t, y_p)
        rec = recall_score(y_t, y_p, average='macro', zero_division=0)
        fpr, fnr = get_fpr_fnr(y_t, y_p, xgb_model.classes_)
        return {"Accuracy": acc, "Recall": rec, "FPR": fpr, "FNR": fnr}
    
    gender_metrics = {
        "Male": evaluate_subset(male_mask),
        "Female": evaluate_subset(female_mask)
    }
    
    # Age subsets
    age = X_test_full['age']
    age_masks = {
        "0-18": age <= 18,
        "19-40": (age > 18) & (age <= 40),
        "41-60": (age > 40) & (age <= 60),
        "60+": age > 60
    }
    
    age_metrics = {
        group: evaluate_subset(mask) for group, mask in age_masks.items()
    }
    
    # 9. BIAS DETECTION
    bias_details = {}
    bias_detected = False
    
    # Gender bias detection
    m_res = gender_metrics["Male"]
    f_res = gender_metrics["Female"]
    if m_res and f_res:
        for metric in ["Accuracy", "Recall", "FPR", "FNR"]:
            diff = abs(m_res[metric] - f_res[metric])
            if diff > 0.1:
                bias_detected = True
                bias_details[f"Gender_{metric}"] = f"BIAS DETECTED (Difference: {diff:.2%})"
                
    # Age bias detection
    valid_age_res = {k: v for k, v in age_metrics.items() if v is not None}
    if valid_age_res:
        for metric in ["Accuracy", "Recall", "FPR", "FNR"]:
            vals = [res[metric] for res in valid_age_res.values()]
            if vals and (max(vals) - min(vals) > 0.1):
                 bias_detected = True
                 bias_details[f"Age_{metric}"] = f"BIAS DETECTED (Max Difference: {max(vals) - min(vals):.2%})"
                 
    # 10. CLEAN OUTPUT STRUCTURE
    recommended_model = "model_b" if xgb_acc > rf_acc else "model_a"
    
    results = {
        "model_a": model_a_results,
        "model_b": model_b_results,
        "gender_metrics": gender_metrics,
        "age_metrics": age_metrics,
        "macro_fpr": overall_fpr,
        "macro_fnr": overall_fnr,
        "bias_flag": "BIAS DETECTED" if bias_detected else "NO SIGNIFICANT BIAS",
        "bias_details": bias_details if bias_details else {"Status": "All metric differences <= 10%"},
        "model_comparison": {
            "Accuracy_Diff": abs(xgb_acc - rf_acc),
            "Top_3_Accuracy_Diff": abs(xgb_top3_acc - rf_top3_acc)
        },
        "recommended_model": recommended_model
    }
    
    print("\n--- MODEL EVALUATION REPORT ---")
    print(json.dumps(results, indent=4))
    
    report_path = os.path.join(MODELS_DIR, "model_evaluation_report.json")
    with open(report_path, "w") as f:
        json.dump(results, f, indent=4)
    print(f"\nReport saved to {report_path}")

if __name__ == "__main__":
    main()


import pandas as pd
import json
import sys
import re
import os
from collections import Counter

def normalize_disease_name(disease):
    if not isinstance(disease, str):
        return str(disease)
    disease = disease.replace("...", "")
    disease = disease.lower().strip()
    disease = re.sub(r'[^a-z0-9\s\-\(\)]', '', disease)
    disease = re.sub(r'\s+', ' ', disease)
    return disease

def main():
    print("=== PIPELINE AUDIT START ===")
    
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    RAW_DIR = os.path.join(DATA_DIR, "raw")
    PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
    REPORTS_DIR = os.path.join(BASE_DIR, "reports")
    
    # Load Training and Patient Datasets
    try:
        X_train = pd.read_csv(os.path.join(PROCESSED_DIR, 'fair_X_train.csv'))
        X_patient = pd.read_csv(os.path.join(PROCESSED_DIR, 'fair_X_test_patient.csv'))
        y_train = pd.read_csv(os.path.join(PROCESSED_DIR, 'y_train_labels.csv'))
        y_patient = pd.read_csv(os.path.join(PROCESSED_DIR, 'fair_y_test_patient.csv'))
    except Exception as e:
        print(f"Error loading datasets: {e}")
        return

    print("\n--------------------------------")
    print("1. DATASET SHAPE & SUMMARY")
    print("--------------------------------")
    print(f"- Shape of training dataset: {X_train.shape[0]} rows, {X_train.shape[1]} columns")
    print(f"- Shape of patient dataset: {X_patient.shape[0]} rows, {X_patient.shape[1]} columns")
    print(f"- Number of feature columns: {X_train.shape[1]}")
    print(f"- Number of samples in training dataset: {X_train.shape[0]}")
    print(f"- Number of samples in patient dataset: {X_patient.shape[0]}")
    
    # Load metadata classes
    with open(os.path.join(PROCESSED_DIR, 'preprocessing_metadata.json'), 'r') as f:
        meta = json.load(f)
    classes = meta['classes']
    train_diseases = set(classes)
    
    patient_disease_texts = [classes[int(val)] for val in y_patient.values.flatten()]
    patient_diseases = set(patient_disease_texts)

    with open(os.path.join(REPORTS_DIR, 'data_cleaning_report.json'), 'r') as f:
        report = json.load(f)
    dropped_diseases_list = report.get('unmatched_dropped_diseases', [])
    
    print("\n--------------------------------")
    print("2. DISEASE COVERAGE")
    print("--------------------------------")
    common_diseases = train_diseases.intersection(patient_diseases)
    only_in_train = train_diseases - patient_diseases
    
    print(f"- Total number of UNIQUE diseases in training dataset: {len(train_diseases)}")
    print(f"- Total number of UNIQUE diseases in patient dataset (after cleaning): {len(patient_diseases)}")
    print(f"- Number of COMMON diseases between both datasets: {len(common_diseases)}")
    print(f"- Number of diseases ONLY in training dataset: {len(only_in_train)}")
    print(f"- Number of diseases that were dropped: {len(dropped_diseases_list)}")
    
    # 3. Label Consistency Check
    print("\n--------------------------------")
    print("3. LABEL CONSISTENCY CHECK")
    print("--------------------------------")
    errors = []
    
    for d in patient_diseases.union(train_diseases):
        if "..." in d:
            errors.append(f"Truncated label found: {d}")
        norm = normalize_disease_name(d)
        if d != norm:
            errors.append(f"Not perfectly normalized: '{d}' -> should be '{norm}'")
            
    if not patient_diseases.issubset(train_diseases):
        errors.append("Some patient diseases are NOT physically in the training dataset!")
        
    if not errors:
        print("VERIFIED: No truncated names exist.")
        print("VERIFIED: All disease names are normalized.")
        print("VERIFIED: All patient dataset diseases exist in training dataset.")
    else:
        for e in errors:
            print(f"ERROR: {e}")
            
    # 4. Mapping validation
    print("\n--------------------------------")
    print("4. MAPPING VALIDATION")
    print("--------------------------------")
    mapped = report.get('mapped_diseases', {})
    print(f"- Total number of disease mappings applied: {len(mapped)}")
    
    suspicious = []
    for old_d, new_d in mapped.items():
        if ("hyper" in old_d and "hypo" in new_d) or ("hypo" in old_d and "hyper" in new_d):
            suspicious.append({"from": old_d, "to": new_d})
    
    if suspicious:
        print(f"Suspicious mappings found ({len(suspicious)}):")
        for s in suspicious:
            print(f"  {s['from']} -> {s['to']}")
    else:
        print("No suspicious 'hyper/hypo' mappings found.")
        
    # 5. Data Loss Analysis
    print("\n--------------------------------")
    print("5. DATA LOSS ANALYSIS")
    print("--------------------------------")
    print(f"- Total rows before preprocessing: {report.get('total_rows_before_processing', 0)}")
    print(f"- Rows dropped before mapping: {report.get('rows_dropped_before_mapping', 0)}")
    print(f"- Rows recovered after mapping: {report.get('rows_recovered_after_mapping', 0)}")
    print(f"- Final rows dropped: {report.get('final_rows_dropped_after_filtering', 0)}")
    print(f"- Final rows retained: {report.get('final_remaining_rows', 0)}")
    pct_dropped = report.get('percentage_dropped_final', 0.0)
    print(f"- Percentage dropped: {pct_dropped:.2f}%")
    
    # 6. Feature consistency
    print("\n--------------------------------")
    print("6. FEATURE CONSISTENCY CHECK")
    print("--------------------------------")
    list_t = list(X_train.columns)
    list_p = list(X_patient.columns)
    if list_t == list_p:
        print("VERIFIED: Training and patient datasets have SAME feature columns")
        print("VERIFIED: No missing columns")
        print("VERIFIED: No extra columns")
    else:
        errors.append("Feature mismatch between sets.")
        
    for prot in ['age', 'gender_female', 'gender_male']:
        if prot in X_patient.columns:
            print(f"CONFIRMED: {prot} is present")
        else:
            errors.append(f"Missing protected attribute: {prot}")

    print("\n--- BIAS DISTRIBUTION (PATIENT DATA) ---")
    f_count = float(X_patient['gender_female'].sum()) if 'gender_female' in X_patient.columns else 0.0
    m_count = float(X_patient['gender_male'].sum()) if 'gender_male' in X_patient.columns else 0.0
    print(f"Gender Dist: Female={f_count}, Male={m_count}")
    if 'age' in X_patient.columns:
        print(f"Age Dist: min={X_patient['age'].min()}, max={X_patient['age'].max()}, mean={X_patient['age'].mean():.2f}")

    # 7. Class Imbalance Report
    print("\n--------------------------------")
    print("7. CLASS IMBALANCE REPORT")
    print("--------------------------------")
    train_counts = Counter(classes[int(v)] for v in y_train.values.flatten())
    most = train_counts.most_common()
    top10 = most[:10]
    bottom10 = most[-10:]
    print("Top 10 most frequent diseases:")
    for d, c in top10:
        print(f"  {d}: {c}")
    print("\nBottom 10 least frequent diseases:")
    for d, c in bottom10:
        print(f"  {d}: {c}")
        
    # 8. Metadata linking
    print("\n--------------------------------")
    print("8. METADATA LINKING CHECK")
    print("--------------------------------")
    meta_files = ['description.csv', 'diets.csv', 'medications.csv', 'precautions.csv', 'workout.csv']
    meta_diseases = set()
    for mf in meta_files:
        try:
            df_m = pd.read_csv(os.path.join(RAW_DIR, mf))
            if 'Disease' in df_m.columns:
                m_list = [normalize_disease_name(d) for d in df_m['Disease'].dropna()]
                meta_diseases.update(m_list)
        except Exception as e:
            print(f"Warning: {e}")
            
    missing_metadata = train_diseases - meta_diseases
    cov = ((len(train_diseases) - len(missing_metadata)) / len(train_diseases)) * 100
    print(f"Total training diseases: {len(train_diseases)}")
    print(f"Diseases with metadata: {len(train_diseases) - len(missing_metadata)}")
    print(f"Missing metadata: {len(missing_metadata)}")
    print(f"Coverage: {cov:.1f}%")
    print("\nSample missing diseases:")
    print(json.dumps(list(missing_metadata)[:20], indent=2))
    
    # 9. & 10. export
    print("\n--------------------------------")
    print("9. FINAL STATUS")
    print("--------------------------------")
    
    if len(suspicious) > 0:
        errors.append(f"Found {len(suspicious)} suspicious mappings (opposite meanings/hyper vs hypo).")

    if not errors:
        status = "PIPELINE STATUS: READY"
    else:
        status = "PIPELINE STATUS: ISSUES REMAIN"
        
    print(status)
    if "ISSUES" in status:
        print("\nIssues:")
        for e in errors:
            print(f" - {e}")

    audit_out = {
        "dataset_shapes": {
            "training_rows": int(X_train.shape[0]),
            "training_columns": int(X_train.shape[1]),
            "patient_rows": int(X_patient.shape[0]),
            "patient_columns": int(X_patient.shape[1])
        },
        "disease_coverage": {
            "total_train_unique": len(train_diseases),
            "total_patient_unique": len(patient_diseases),
            "common": len(common_diseases),
            "only_train": len(only_in_train),
            "dropped": len(dropped_diseases_list),
            "final_model_diseases_list": list(train_diseases),
            "dropped_diseases_list": dropped_diseases_list
        },
        "mapping_validation": {
            "total_applied": len(mapped),
            "mapping_dictionary": mapped,
            "suspicious_mappings": suspicious,
            "rejected_mappings": report.get('rejected_mappings', [])
        },
        "data_loss_analysis": {
            "total_rows_before": report.get('total_rows_before_processing', 0),
            "rows_dropped_initial": report.get('rows_dropped_before_mapping', 0),
            "rows_recovered": report.get('rows_recovered_after_mapping', 0),
            "final_rows_dropped": report.get('final_rows_dropped_after_filtering', 0),
            "final_rows_retained": report.get('final_remaining_rows', 0),
            "percentage_dropped": pct_dropped
        },
        "bias_distribution": {
            "gender_female": float(f_count),
            "gender_male": float(m_count),
            "age_min": float(X_patient['age'].min()) if 'age' in X_patient.columns else 0,
            "age_max": float(X_patient['age'].max()) if 'age' in X_patient.columns else 0,
            "age_mean": float(X_patient['age'].mean()) if 'age' in X_patient.columns else 0
        },
        "class_imbalance": {
            "top_10": dict(top10),
            "bottom_10": dict(bottom10)
        },
        "metadata_coverage": {
            "total": len(train_diseases),
            "with_metadata": len(train_diseases) - len(missing_metadata),
            "missing": len(missing_metadata),
            "coverage_percent": cov,
            "sample_missing": list(missing_metadata)[:20]
        },
        "status": status,
        "errors": errors
    }
    
    with open(os.path.join(REPORTS_DIR, 'final_pipeline_audit_report_v2.json'), 'w') as f:
        json.dump(audit_out, f, indent=4)
    
    print("\n--------------------------------")
    print("10. OUTPUT REPORT")
    print("--------------------------------")
    print("Report written to: final_pipeline_audit_report_v2.json")
    
if __name__ == '__main__':
    main()

import pandas as pd
import numpy as np
import ast
import json
import os
import re
from rapidfuzz import process, fuzz
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
from sklearn.utils.class_weight import compute_class_weight

def clean_column_names(df):
    df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_')
    return df

def clean_general_data(file_path):
    df = pd.read_csv(file_path)
    df = clean_column_names(df)
    
    # Strip whitespace from string columns
    str_cols = df.select_dtypes(include=['object']).columns
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip().str.lower()
        
    # Drop full duplicates
    df = df.drop_duplicates().reset_index(drop=True)
    return df

def process_clinical_metadata(raw_dir, processed_dir):
    print("Processing clinical metadata...")
    diets = clean_general_data(os.path.join(raw_dir, 'diets.csv'))
    meds = clean_general_data(os.path.join(raw_dir, 'medications.csv'))
    workouts = clean_general_data(os.path.join(raw_dir, 'workout.csv'))
    precautions = clean_general_data(os.path.join(raw_dir, 'precautions.csv'))
    
    # Transform list strings to proper lists
    def parse_lists(series):
        def _parse(x):
            try:
                return ast.literal_eval(x)
            except:
                return [x]
        return series.apply(_parse)
    
    diets['diet'] = parse_lists(diets['diet'])
    meds['medication'] = parse_lists(meds['medication'])
    workouts['workouts'] = parse_lists(workouts['workouts'])
    
    # Normalize precautions into single list
    precaution_cols = [c for c in precautions.columns if c.startswith('precaution')]
    precautions['precautions'] = precautions[precaution_cols].values.tolist()
    # Remove Nans and empty strings from the list
    precautions['precautions'] = precautions['precautions'].apply(
        lambda x: [str(item).strip() for item in x if str(item).strip() and str(item).strip() != 'nan']
    )
    precautions = precautions[['disease', 'precautions']]
    
    # Export cleaned metadata iteratively
    diets.to_json(os.path.join(processed_dir, "diets_cleaned.json"), orient='records')
    meds.to_json(os.path.join(processed_dir, "medications_cleaned.json"), orient='records')
    workouts.to_json(os.path.join(processed_dir, "workout_cleaned.json"), orient='records')
    precautions.to_json(os.path.join(processed_dir, "precautions_cleaned.json"), orient='records')
    print("Exported metadata to JSON.")

def normalize_disease_name(name):
    if not isinstance(name, str):
        return str(name)
    name = name.lower()
    name = name.replace('...', '')
    
    # Strip non-alphanumeric except for space, hyphen and parentheses
    name = re.sub(r'[^a-z0-9\s\-\(\)]', '', name)
    
    name = name.strip()
    name = re.sub(r'\s+', ' ', name)
    return name

def normalize_tokens(name):
    name = str(name).lower()
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    words = name.split()
    clean_words = []
    
    suffixes_to_remove = {"disease", "syndrome", "disorder", "condition"}
    for w in words:
        if w in ["crohns", "alzheimers", "parkinsons"]:
            w = w[:-1]
        if w not in suffixes_to_remove:
            clean_words.append(w)
            
    return clean_words

def is_contradiction(w1, w2):
    set1 = set(w1)
    set2 = set(w2)
    pairs = [("hyper", "hypo"), ("acute", "chronic"), ("benign", "malignant")]
    for p1, p2 in pairs:
        has_p1 = any(p1 in w for w in set1)
        has_p2_1 = any(p2 in w for w in set1)
        
        has_p1_2 = any(p1 in w for w in set2)
        has_p2_2 = any(p2 in w for w in set2)
        
        if (has_p1 and has_p2_2) or (has_p2_1 and has_p1_2):
            return True
            
    return False

def map_disease_names(patient_diseases, valid_train_diseases):
    mapping = {}
    unmatched = []
    suspicious_attempts = []
    rejected_mappings = []
    
    manual_mappings = {
      "influenza": "flu",
      "hypertension": "high blood pressure",
      "myocardial infarction": "heart attack",
      "bronchitis": "acute bronchitis",
      "sinusitis": "acute sinusitis"
    }
    
    train_tokens = {td: normalize_tokens(td) for td in valid_train_diseases}
    train_token_sets = {td: set(train_tokens[td]) for td in valid_train_diseases}
    
    for p_disease in patient_diseases:
        if p_disease in valid_train_diseases:
            mapping[p_disease] = p_disease
            continue
            
        if p_disease in manual_mappings and manual_mappings[p_disease] in valid_train_diseases:
            mapping[p_disease] = manual_mappings[p_disease]
            continue
            
        p_tokens = normalize_tokens(p_disease)
        if not p_tokens:
            unmatched.append(p_disease)
            continue
            
        match = process.extractOne(p_disease, valid_train_diseases, scorer=fuzz.token_set_ratio)
        if match and match[1] >= 90:
            target_disease = match[0]
            t_tokens = train_tokens[target_disease]
            
            if is_contradiction(p_tokens, t_tokens):
                rejected_mappings.append({"from": p_disease, "to": target_disease, "reason": "contradiction_tokens"})
                suspicious_attempts.append({"from": p_disease, "to": target_disease})
                unmatched.append(p_disease)
                continue
                
            shared_core = set(p_tokens).intersection(train_token_sets[target_disease])
            if not shared_core:
                rejected_mappings.append({"from": p_disease, "to": target_disease, "reason": "no_core_term_match"})
                unmatched.append(p_disease)
                continue
                
            mapping[p_disease] = target_disease
        else:
            unmatched.append(p_disease)
            
    return mapping, unmatched, rejected_mappings, suspicious_attempts

def main():
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    RAW_DIR = os.path.join(DATA_DIR, "raw")
    PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
    REPORTS_DIR = os.path.join(BASE_DIR, "reports")
    
    # Process metadata
    process_clinical_metadata(RAW_DIR, PROCESSED_DIR)
    
    # Process Symptom Data
    print("Processing symptom matrices...")
    base_symptoms = clean_general_data(os.path.join(RAW_DIR, 'Diseases_and_Symptoms_dataset.csv'))
    aug_symptoms = clean_general_data(os.path.join(RAW_DIR, 'Final_Augmented_dataset_Diseases_and_Symptoms.csv'))
    
    base_symptoms['diseases'] = base_symptoms['diseases'].apply(normalize_disease_name)
    aug_symptoms['diseases'] = aug_symptoms['diseases'].apply(normalize_disease_name)
    
    # Align symptom columns - Take Union
    base_features = set(base_symptoms.columns) - {'diseases'}
    aug_features = set(aug_symptoms.columns) - {'diseases'}
    all_features = sorted(list(base_features.union(aug_features)))
    
    for df in [base_symptoms, aug_symptoms]:
        for col in all_features:
            if col not in df.columns:
                df[col] = 0
                
    base_symptoms = base_symptoms[['diseases'] + all_features]
    aug_symptoms = aug_symptoms[['diseases'] + all_features]
    
    # Ensure binary
    for col in all_features:
        aug_symptoms[col] = aug_symptoms[col].apply(lambda x: 1 if float(x) > 0 else 0)
        
    # Fit Label Encoder
    le = LabelEncoder()
    aug_symptoms['diseases_encoded'] = le.fit_transform(aug_symptoms['diseases'])
    
    X_train = aug_symptoms[all_features].copy()
    y_train = aug_symptoms['diseases_encoded'].copy()
    
    # Imbalance handling
    classes = np.unique(y_train)
    weights = compute_class_weight(class_weight='balanced', classes=classes, y=y_train)
    class_weights_dict = {int(k): float(v) for k, v in zip(classes, weights)}
    
    value_counts = aug_symptoms['diseases'].value_counts()
    rare_classes = value_counts[value_counts < 5].index.tolist()
    print(f"Flagged {len(rare_classes)} rare classes with <5 samples.")
    
    # Export Training Data
    aug_symptoms.drop(columns=['diseases']).to_csv(os.path.join(PROCESSED_DIR, 'X_train_final.csv'), index=False)
    X_train.to_csv(os.path.join(PROCESSED_DIR, 'X_train_features.csv'), index=False)
    y_train.to_csv(os.path.join(PROCESSED_DIR, 'y_train_labels.csv'), index=False)
    
    print("Processing Patient Dataset...")
    patient_df = clean_general_data(os.path.join(RAW_DIR, 'Disease_symptom_and_patient_profile_dataset.csv'))
    
    # Drop Outcome Variable completely
    if 'outcome_variable' in patient_df.columns:
        patient_df = patient_df.drop(columns=['outcome_variable'])
        
    valid_train_diseases = set(aug_symptoms['diseases'].unique())
    
    # Normalize Patient Labels
    patient_df['disease'] = patient_df['disease'].apply(normalize_disease_name)
    
    # MAPPING LOGIC
    total_rows = len(patient_df)
    
    unseen_before_mapping_mask = ~patient_df['disease'].isin(valid_train_diseases)
    rows_dropped_before = unseen_before_mapping_mask.sum()
    
    unique_patient_diseases = patient_df['disease'].unique()
    mapping_dict, unmatched_diseases, rejected_mappings, suspicious_attempts = map_disease_names(unique_patient_diseases, valid_train_diseases)
    
    # Apply Mapping
    patient_df['disease'] = patient_df['disease'].map(lambda x: mapping_dict.get(x, x))
    
    unseen_after_mapping_mask = ~patient_df['disease'].isin(valid_train_diseases)
    rows_dropped_after = unseen_after_mapping_mask.sum()
    rows_recovered = rows_dropped_before - rows_dropped_after
    
    retained_rows = total_rows - rows_dropped_after
    pct_dropped = (rows_dropped_after / total_rows) * 100
    pct_retained = (retained_rows / total_rows) * 100
    
    mapped_diseases_log = {k: v for k, v in mapping_dict.items() if k != v}
    
    filtering_stats = {
        "total_rows_before_processing": int(total_rows),
        "rows_dropped_before_mapping": int(rows_dropped_before),
        "rows_recovered_after_mapping": int(rows_recovered),
        "final_rows_dropped_after_filtering": int(rows_dropped_after),
        "final_remaining_rows": int(retained_rows),
        "percentage_dropped_final": round(pct_dropped, 2),
        "percentage_retained_final": round(pct_retained, 2),
        "mapped_diseases": mapped_diseases_log,
        "rejected_mappings": rejected_mappings,
        "suspicious_attempts": suspicious_attempts,
        "unmatched_diseases_dropped": [str(d) for d in unmatched_diseases]
    }
    
    with open(os.path.join(REPORTS_DIR, "data_cleaning_report.json"), "w") as f:
        json.dump(filtering_stats, f, indent=4)
        
    old_report_file = os.path.join(REPORTS_DIR, "patient_filtering_report.json")
    if os.path.exists(old_report_file):
        try:
            os.remove(old_report_file)
            print(f"Removed old report: {old_report_file}")
        except OSError as e:
            print(f"Error removing {old_report_file}: {e}")
        
    # Apply filtering
    patient_df = patient_df[~unseen_after_mapping_mask].reset_index(drop=True)
    
    # Validation checks
    assert not any(str(d).endswith('...') for d in valid_train_diseases), "Truncated labels remain in training data!"
    assert not any(str(d).endswith('...') for d in patient_df['disease'].unique()), "Truncated labels remain in patient data!"
    assert patient_df['disease'].isin(valid_train_diseases).all(), "Unmatched labels found in patient dataset after filtering!"
    assert len(patient_df['disease'].unique()) == len(set(patient_df['disease'].unique())), "Duplicate disease names detected!"
    
    print("Patient Targeting Output Summary:")
    print(f"Total rows before filtering: {total_rows}")
    print(f"Rows dropped before mapping: {rows_dropped_before}")
    print(f"Rows recovered after mapping: {rows_recovered}")
    print(f"Final rows dropped: {rows_dropped_after}")
    print(f"Final rows remaining: {retained_rows}")
    print(f"Percentage dropped: {pct_dropped:.2f}%")
    print(f"Percentage retained: {pct_retained:.2f}%")
    print(f"Unmatched dropped diseases count: {len(unmatched_diseases)}")
    
    # Feature engineering for Patient Data
    # Categorical fields
    patient_df = pd.get_dummies(patient_df, columns=['gender', 'blood_pressure', 'cholesterol_level'], prefix=['gender', 'bp', 'chol'])
    
    # Align Patient Features with X_train
    # Preserve Age and Gender fields + bp, chol + disease
    protected_and_eng = ['disease', 'age'] + [c for c in patient_df.columns if c.startswith('gender_') or c.startswith('bp_') or c.startswith('chol_')]
    
    # Check if patient columns match any training symptoms and rename them to match
    for col in patient_df.columns:
        if col.replace(' ', '_') in all_features:
            patient_df.rename(columns={col: col.replace(' ', '_')}, inplace=True)
            
    patient_final_cols = list(set(protected_and_eng + all_features))
    for col in patient_final_cols:
        if col not in patient_df.columns:
            patient_df[col] = 0
            
    # Add engineered features back to X_train as 0 (for true alignment)
    for col in set(protected_and_eng) - {'disease'}:
        if col not in X_train.columns:
            X_train[col] = 0
            
    # Sort columns for absolute parity
    final_ordered_columns = sorted(list(set(patient_final_cols) - {'disease'}))
    
    # Final feature alignment!
    X_train_final = X_train[final_ordered_columns].copy() 
    X_test_final = patient_df[final_ordered_columns].copy()
    
    # Validation checks for Feature Consistency
    assert list(X_train_final.columns) == list(X_test_final.columns), "Feature misalignment detected!"
    assert 'age' in X_train_final.columns, "'age' column missing!"
    
    # Generate labels
    y_test_final = le.transform(patient_df['disease'])
    
    # Export Outputs
    X_train_final.to_csv(os.path.join(PROCESSED_DIR, "fair_X_train.csv"), index=False)
    X_test_final.to_csv(os.path.join(PROCESSED_DIR, "fair_X_test_patient.csv"), index=False)
    pd.DataFrame(y_train, columns=['disease_label']).to_csv(os.path.join(PROCESSED_DIR, "fair_y_train.csv"), index=False)
    pd.DataFrame(y_test_final, columns=['disease_label']).to_csv(os.path.join(PROCESSED_DIR, "fair_y_test_patient.csv"), index=False)
    
    # Export Metadata
    metadata_export = {
        "features": final_ordered_columns,
        "classes": list(le.classes_), # Disease string classes
        "class_weights": class_weights_dict,
        "patient_filtering_stats": filtering_stats
    }
    with open(os.path.join(PROCESSED_DIR, "preprocessing_metadata.json"), "w") as f:
        json.dump(metadata_export, f, indent=4)
        
    print("Finished successfully. Artifacts dumped to disk.")

if __name__ == "__main__":
    main()

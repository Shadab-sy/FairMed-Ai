import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import os
import re
import warnings

warnings.filterwarnings('ignore')

# ---------------------------------------------------------
# Step 1: Load and Clean Data
# ---------------------------------------------------------

def clean_text(text):
    """
    Standardize text:
    - Lowercase
    - Remove spaces and special characters
    - Replace spaces with underscores
    """
    if pd.isna(text):
        return text
    text = str(text).lower().strip()
    # Remove special chars except spaces and underscores
    text = re.sub(r'[^a-z0-9\s_]', '', text)
    # Replace single or multiple spaces/underscores with a single underscore
    text = re.sub(r'[\s_]+', '_', text)
    # Strip leading and trailing underscores
    text = text.strip('_')
    return text

def load_and_clean_data(data_dir='.'):
    print("Step 1: Loading and Cleaning Data...")
    
    file_map = {
        'dataset': 'dataset.csv',
        'severity': 'Symptom-severity.csv',
        'description': 'symptom_Description.csv',
        'precaution': 'symptom_precaution.csv',
        'disease_profile': 'Disease_symptom_and_patient_profile_dataset.csv',
        'insurance': 'insurance.csv'
    }
    
    dfs = {}
    for key, filename in file_map.items():
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            dfs[key] = pd.read_csv(filepath)
            print(f"  - Loaded {filename}")
        else:
            print(f"  - WARNING: File {filename} not found. Proceeding with empty dataframe.")
            dfs[key] = pd.DataFrame()

    # Clean the column names and string content across all loaded datasets
    for key, df in dfs.items():
        if df.empty:
            continue
        
        # Standardize column naming
        df.columns = [clean_text(col) for col in df.columns]
        
        # Standardize string values in cells
        str_cols = df.select_dtypes(include=['object']).columns
        for col in str_cols:
            df[col] = df[col].apply(clean_text)
            
    return dfs

# ---------------------------------------------------------
# Step 2: Symptom Normalization
# ---------------------------------------------------------

def normalize_symptoms(df_dataset):
    """
    Extract unique symptoms, create a master list, and perform one-hot encoding.
    """
    print("\nStep 2: Symptom Normalization...")
    if df_dataset.empty:
        return pd.DataFrame(), []
        
    symptom_cols = [col for col in df_dataset.columns if 'symptom' in col.lower()]
    
    # Create master list
    master_symptoms = set()
    for col in symptom_cols:
        master_symptoms.update(df_dataset[col].dropna().unique())
    master_symptoms = sorted([s for s in master_symptoms if s]) # filter out empty strings
    
    # Perform One-hot encoding
    encoded_rows = []
    
    for _, row in df_dataset.iterrows():
        disease = row.get('disease')
        # Patient's specific symptoms as a set for faster lookup
        patient_symptoms = {row[col] for col in symptom_cols if pd.notna(row[col])}
        
        encoded_dict = {'disease': disease}
        for symptom in master_symptoms:
            encoded_dict[symptom] = 1 if symptom in patient_symptoms else 0
            
        encoded_rows.append(encoded_dict)
        
    df_encoded = pd.DataFrame(encoded_rows)
    print(f"  - Found {len(master_symptoms)} unique symptoms.")
    return df_encoded, master_symptoms

# ---------------------------------------------------------
# Step 3: Integrate Symptom Severity
# ---------------------------------------------------------

def integrate_symptom_severity(df_encoded, df_severity, master_symptoms):
    """
    Map symptom weights to the binary symptom vector.
    """
    print("\nStep 3: Integrating Symptom Severity...")
    if df_encoded.empty or df_severity.empty:
        return df_encoded
        
    # df_severity is expected to have 'symptom' and 'weight' columns after cleaning
    if 'symptom' not in df_severity.columns or 'weight' not in df_severity.columns:
        print("  - WARNING: Expected columns 'symptom' and 'weight' not found. Skipping weighting.")
        return df_encoded
        
    weight_dict = dict(zip(df_severity['symptom'], df_severity['weight']))
    
    df_weighted = df_encoded.copy()
    count_weighted = 0
    
    for symptom in master_symptoms:
        if symptom in weight_dict:
            try:
                weight = float(weight_dict[symptom])
                df_weighted[symptom] = df_weighted[symptom] * weight
                count_weighted += 1
            except ValueError:
                pass
                
    print(f"  - Applied weights to {count_weighted} symptoms.")
    return df_weighted

# ---------------------------------------------------------
# Step 4: Prepare Training Dataset
# ---------------------------------------------------------

def prepare_training_data(df_weighted):
    """
    Split sets and encode target labels.
    """
    print("\nStep 4: Preparing Training Dataset...")
    if df_weighted.empty:
        return pd.DataFrame()
        
    # Important constraint: Remove age/gender from main training model features
    cols_to_exclude = ['disease', 'age', 'gender']
    
    X = df_weighted.drop(columns=[col for col in cols_to_exclude if col in df_weighted.columns])
    y = df_weighted['disease']
    
    # Label encoding target
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)
    print(f"  - Training Data Shape (X_train): {X_train.shape}")
    print(f"  - Test Data Shape (X_test): {X_test.shape}")
    
    # Create final compiled training payload
    df_final = X.copy()
    df_final['disease'] = y
    df_final['disease_label'] = y_encoded
    
    return df_final

# ---------------------------------------------------------
# Step 5: Prepare Fairness Dataset
# ---------------------------------------------------------

def prepare_fairness_dataset(df_profile, master_symptoms):
    """
    Extract fairness metrics (age, gender, symptoms) and align them.
    """
    print("\nStep 5: Preparing Fairness Dataset...")
    if df_profile.empty:
        return pd.DataFrame()
        
    df_fairness = df_profile.copy()
    
    # Convert Yes/No strings into pure binary (1, 0)
    for col in df_fairness.columns:
        if df_fairness[col].dtype == 'object':
            unique_vals = [str(x).lower() for x in df_fairness[col].dropna().unique()]
            if 'yes' in unique_vals or 'no' in unique_vals:
                df_fairness[col] = df_fairness[col].map(
                    lambda x: 1 if str(x).lower() in ['yes', '1', 'true'] 
                    else (0 if str(x).lower() in ['no', '0', 'false'] else x)
                )

    # Attempt symptom alignment with main dataset where column name matches master list
    aligned_symptoms_count = 0
    for col in df_fairness.columns:
        if col in master_symptoms:
            aligned_symptoms_count += 1
            
    # Retain strictly the target variable, symptoms, age, and gender elements
    # Using outcome_variable or disease as target, retaining all features for analysis
    print(f"  - Extracted demographic context alongside {aligned_symptoms_count} matched symptoms.")
    return df_fairness

# ---------------------------------------------------------
# Step 6: Data Validation
# ---------------------------------------------------------

def validate_data(df, df_name="Dataset"):
    """
    Run validation routines over the dataset.
    """
    print(f"\nStep 6: Data Validation for [{df_name}]...")
    if df.empty:
        print("  - Dataframe is empty.")
        return
        
    duplicates = df.duplicated().sum()
    print(f"  - Potential duplicate rows: {duplicates}")
    
    null_count = df.isnull().sum().sum()
    print(f"  - Missing global values (NaN): {null_count}")
    
    if 'disease' in df.columns:
        counts = df['disease'].value_counts()
        print(f"  - Class distribution top counts:\n{counts.head(4).to_string()}")
        imbalance_ratio = counts.max() / max(1, counts.min())
        print(f"  - Class imbalance ratio: {imbalance_ratio:.2f}")
        if imbalance_ratio > 10:
            print("  ! WARNING: Substantial class imbalance detected in 'disease'.")
            
    print(f"  - Overall Shape: {df.shape}")

# ---------------------------------------------------------
# Step 7: Save Processed Data
# ---------------------------------------------------------

def save_data(df_train, master_symptoms, df_fairness, output_dir='.'):
    """
    Dumps memory DataFrames back to local persistent storage.
    """
    print("\nStep 7: Saving Processed Data...")
    
    train_path = os.path.join(output_dir, 'cleaned_training_data.csv')
    if not df_train.empty:
        df_train.to_csv(train_path, index=False)
        print(f"  - Generated {train_path}")

    symptoms_path = os.path.join(output_dir, 'master_symptom_list.csv')
    if master_symptoms:
        pd.DataFrame({'symptom_name': master_symptoms}).to_csv(symptoms_path, index=False)
        print(f"  - Generated {symptoms_path}")
        
    fairness_path = os.path.join(output_dir, 'processed_fairness_data.csv')
    if not df_fairness.empty:
        df_fairness.to_csv(fairness_path, index=False)
        print(f"  - Generated {fairness_path}")

# ---------------------------------------------------------
# Orchestration
# ---------------------------------------------------------

def main():
    print("===========================================")
    print(" FairMed AI - Data Preprocessing Pipeline  ")
    print("===========================================\n")
    
    # Target directory mapping. Ensure to run where CSV files are deposited.
    WORKING_DIR = '.'
    
    # Execute Pipeline
    dfs = load_and_clean_data(WORKING_DIR)
    
    # Orchestrate data flow
    df_encoded, master_symptoms = normalize_symptoms(dfs['dataset'])
    df_weighted = integrate_symptom_severity(df_encoded, dfs['severity'], master_symptoms)
    df_train = prepare_training_data(df_weighted)
    df_fairness = prepare_fairness_dataset(dfs['disease_profile'], master_symptoms)
    
    # Validations
    validate_data(df_train, "Compiled Training Dataset")
    if not df_fairness.empty:
        validate_data(df_fairness, "Fairness Evaluation Dataset")
        
    # IO Export
    save_data(df_train, master_symptoms, df_fairness, WORKING_DIR)
    
    print("\n===> Pipeline Execution Complete! <===")

if __name__ == "__main__":
    main()

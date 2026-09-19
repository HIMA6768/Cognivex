import os
import pandas as pd

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
csv_path = os.path.join(DATA_DIR, "METABRIC_RNA_Mutation.csv")
manifest_path = os.path.join(DATA_DIR, "manifest.csv")

def validate():
    print("Validating dataset and splits...")
    df = pd.read_csv(csv_path, low_memory=False)
    manifest = pd.read_csv(manifest_path)
    
    # 1. Validate Cohort Size
    assert len(df) == 1904, f"Expected 1904 patients, got {len(df)}"
    assert len(manifest) == 1904, f"Expected 1904 manifest entries, got {len(manifest)}"
    
    # 2. Validate Splits (No Leakage)
    train_patients = set(manifest[manifest['split'] == 'train']['patient_id'])
    val_patients = set(manifest[manifest['split'] == 'validation']['patient_id'])
    test_patients = set(manifest[manifest['split'] == 'test']['patient_id'])
    
    assert len(train_patients.intersection(val_patients)) == 0, "Leakage between train and validation"
    assert len(train_patients.intersection(test_patients)) == 0, "Leakage between train and test"
    assert len(val_patients.intersection(test_patients)) == 0, "Leakage between validation and test"
    
    print("Validation passed: No patient leakage across splits.")
    print(f"Train: {len(train_patients)}, Validation: {len(val_patients)}, Test: {len(test_patients)}")

if __name__ == "__main__":
    validate()

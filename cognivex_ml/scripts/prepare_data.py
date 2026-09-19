import os
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Automatically find the directory where this script lives (scripts)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")

TRAIN_CSV = os.path.join(DATA_DIR, "train_dataset.csv")
VAL_CSV   = os.path.join(DATA_DIR, "validation_dataset.csv")
TEST_CSV  = os.path.join(DATA_DIR, "test_dataset.csv")

def run_preparation():
    logging.info("Loading pre-split datasets provided by team...")

    frames = []
    for path, split in [(TRAIN_CSV, "train"), (VAL_CSV, "validation"), (TEST_CSV, "test")]:
        logging.info(f"  Loading {split}: {path}")
        tmp = pd.read_csv(path, low_memory=False)
        tmp.columns = tmp.columns.str.strip().str.lower().str.replace(' ', '_')
        tmp['split'] = split
        frames.append(tmp)

    df = pd.concat(frames, ignore_index=True)
    logging.info(f"Combined dataset shape: {df.shape}")

    # --- APPLIED DATA FIXES ---
    logging.info("Applying domain-specific fixes...")
    df = df.replace('Positve', 'Positive')
    df['tumor_stage'] = df['tumor_stage'].fillna('Unknown').astype(str)

    # In the new dataset overall_survival: 1 = Living (censored), 0 = Died (event).
    # For CoxPH we need: event=1 means the event occurred (death), event=0 means censored (living).
    # Therefore the event column = 1 - overall_survival (as original METABRIC encoding fix).
    df['event'] = 1 - pd.to_numeric(df['overall_survival'], errors='coerce')
    logging.info(f"Event (deceased) counts:\n{df['event'].value_counts().to_string()}")

    # 2. Generate patient_mapping.csv
    logging.info("Generating patient ID mapping...")
    mapping = pd.DataFrame({'patient_id': df['patient_id'], 'genomic_sample_id': df['patient_id']})
    mapping_out = os.path.join(DATA_DIR, "patient_mapping.csv")
    mapping.to_csv(mapping_out, index=False)
    logging.info(f"Saved patient mapping to {mapping_out}")

    # 3. Generate manifest.csv from split column
    logging.info("Generating manifest from pre-defined splits...")
    manifest = df[['patient_id', 'split']].copy()
    manifest['data_source'] = 'METABRIC_TeamSelected'
    manifest_out = os.path.join(DATA_DIR, "manifest.csv")
    manifest.to_csv(manifest_out, index=False)
    logging.info(f"Saved manifest to {manifest_out}")

    # 4. Log split sizes
    for s in ['train', 'validation', 'test']:
        n = (manifest['split'] == s).sum()
        logging.info(f"  {s}: {n} patients")

    logging.info("Data preparation completed successfully.")

if __name__ == "__main__":
    run_preparation()
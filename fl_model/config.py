
# Global configuration for the FedSDM pipeline
from pathlib import Path

# ECG CSV location (140 features + 1 label column)
CSV_PATH = Path(__file__).resolve().parent / 'data' / 'ecg.csv'
# If the CSV does not exist, use synthetic data generator
USE_SYNTHETIC_IF_MISSING = True
N_SAMPLES_SYNTH = 2000

# Core data settings
N_FEATURES = 140
TEST_RATIO = 0.2
RANDOM_SEED = 42
CLIENTS = 5

# Model/FL settings
ENCODING_DIM = 48   # bottleneck size (try 32/48/64)
LOCAL_EPOCHS = 5
ROUNDS = 20
BATCH_SIZE = 32

# Output directory
OUTPUT_DIR = Path(__file__).resolve().parent / 'results'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Filenames
MODEL_KERAS = OUTPUT_DIR / 'autoencoder_fed_global.keras'
MODEL_H5    = OUTPUT_DIR / 'autoencoder_fed_global.h5'
CSV_RESULTS = OUTPUT_DIR / 'results_fedsdm.csv'
FIG_ROC     = OUTPUT_DIR / 'roc_curve.png'
FIG_PR      = OUTPUT_DIR / 'pr_curve.png'
SCALER_PKL  = OUTPUT_DIR / 'scaler.pkl'

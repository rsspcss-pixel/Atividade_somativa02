from pathlib import Path

ML_DIR = Path(__file__).resolve().parent
MODELS_DIR = ML_DIR / "models"
MODEL_PATH = MODELS_DIR / "risco_renegociacao.pkl"
METRICS_PATH = MODELS_DIR / "metrics.json"
DATA_CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "ml" / "uci_credit_default.csv"

DATASET_NAME = "Default of Credit Card Clients"
DATASET_SOURCE = "UCI Machine Learning Repository (ID 350)"
DATASET_URL = "https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients"
DOMAIN_TARGET_LABEL = "risco_renegociacao_urgente"

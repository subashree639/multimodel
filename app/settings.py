import os
from pathlib import Path

# Base directory (project root)
BASE_DIR = Path(__file__).resolve().parent.parent

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
MODEL_DIR = BASE_DIR / "models"
MODEL_DIR.mkdir(exist_ok=True)
DATASET_DIR = BASE_DIR / "datasets"
DATASET_DIR.mkdir(exist_ok=True)

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB = "multimodal_product_db"

TOP_N_DEFAULT = 10
CONTENT_WEIGHT = 0.4
COLLAB_WEIGHT = 0.4
SENTIMENT_WEIGHT = 0.2

IMAGE_FEATURE_DIM = 2048
FAISS_INDEX_PATH = str(MODEL_DIR / "faiss_index.bin")
FAISS_IDS_PATH = str(MODEL_DIR / "faiss_ids.pkl")

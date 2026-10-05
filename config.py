"""
Application configuration settings.
"""

import os

# This environment ships TensorFlow + Keras 3, but the project only uses the
# PyTorch side of transformers/sentence-transformers. Without this flag any
# import of `transformers.integrations` raises at load time (Keras 3 is not
# supported), which breaks `sentence_transformers` and the chatbot package.
os.environ.setdefault("USE_TF", "0")

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # MongoDB Configuration
    MONGODB_URL: str = "mongodb://localhost:27017/"
    MONGODB_DB_NAME: str = "multimodal_product_db"

    # JWT Configuration
    SECRET_KEY: str = "your-secret-key-change-in-production-use-env-var"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # File Upload Configuration
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: str = ".jpg,.jpeg,.png,.webp"

    # Model Configuration
    MODEL_DIR: str = "models"
    IMAGE_FEATURE_DIM: int = 2048
    EMBEDDING_DIM: int = 768

    # Recommendation Configuration
    DEFAULT_TOP_N: int = 10
    COLLABORATIVE_FILTER_WEIGHT: float = 0.40   # SVD collaborative filtering (40%)
    CONTENT_BASED_WEIGHT: float = 0.25           # TF-IDF + Cosine Similarity (25%)
    SENTIMENT_WEIGHT: float = 0.20               # Positive sentiment from reviews (20%)
    SALES_TREND_WEIGHT: float = 0.15             # Sales trend & popularity (15%)

    # FAISS Configuration
    FAISS_INDEX_PATH: str = "models/faiss_index.bin"
    FAISS_PRODUCT_IDS_PATH: str = "models/faiss_product_ids.pkl"

    # Chatbot Configuration
    CHATBOT_MODEL: str = "sentence-transformers/all-mpnet-base-v2"
    RAG_TOP_K: int = 5

    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "MultiModal Product Recommendation"
    VERSION: str = "1.0.0"
    CORS_ORIGINS: list = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # Logging
    LOG_LEVEL: str = "INFO"

    # Admin seed account (used by training/ingest_to_mongodb.py)
    ADMIN_EMAIL: str = "admin@multimodal.local"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

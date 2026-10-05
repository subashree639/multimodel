from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "MultiModal Product Recommendation"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "change-me-in-production-use-a-strong-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    MONGODB_URL: str = "mongodb://localhost:27017/"
    MONGODB_DB_NAME: str = "multimodal_product_db"

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    SENTIMENT_MODEL: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    IMAGE_MODEL: str = "resnet50"

    UPLOAD_DIR: str = "uploads"
    MODEL_DIR: str = "models"

    CORS_ORIGINS: list[str] = ["http://localhost:8501", "http://localhost:3000", "http://127.0.0.1:8501"]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

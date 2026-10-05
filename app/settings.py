"""Environment configuration shared by the API, scripts and dashboard."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from fraudgraph.utils.paths import get_project_root

load_dotenv(get_project_root() / ".env")


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///data/banking.db")
    model_path: str = os.getenv("MODEL_PATH", "models/baseline/random_forest.joblib")
    fraud_threshold: float = float(os.getenv("FRAUD_THRESHOLD", "0.80"))
    app_env: str = os.getenv("APP_ENV", "development")

    def __post_init__(self) -> None:
        if not 0 < self.fraud_threshold < 1:
            raise ValueError("FRAUD_THRESHOLD must be between zero and one")


settings = Settings()

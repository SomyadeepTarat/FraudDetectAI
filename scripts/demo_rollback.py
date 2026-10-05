import json

from app.db.session import SessionLocal
from app.services.demos import rollback_demo
from app.services.inference import ModelInference
from app.settings import settings

if __name__ == "__main__":
    print(
        json.dumps(
            rollback_demo(SessionLocal, ModelInference(settings.model_path)), indent=2
        )
    )

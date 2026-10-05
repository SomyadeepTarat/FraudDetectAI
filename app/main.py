"""Run with PYTHONPATH=src:. uvicorn app.main:app --reload."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.routes import router
from app.services.transactions import BankingError

app = FastAPI(title="FraudDetectAI Banking Database", version="1.0.0")
app.include_router(router)


@app.exception_handler(BankingError)
async def banking_error(request: Request, exc: BankingError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(IntegrityError)
async def integrity_error(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409,
        content={
            "detail": "Database constraint rejected the operation; no changes committed."
        },
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Database operation failed; no changes committed. Check database connection and migrations."
        },
    )


@app.get("/health")
def health():
    return {"status": "ok"}

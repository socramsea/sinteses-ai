from fastapi import FastAPI

from app.api.routes_jobs import router as jobs_router
from app.logging_conf import setup_logging

setup_logging()

app = FastAPI(title="Síntese — Documentary Synthesis Engine", version="0.1.0")
app.include_router(jobs_router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "service": "sintese"}

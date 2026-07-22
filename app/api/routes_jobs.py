"""Rotas de job. Submissão é assíncrona: 202 + job_id; consulta por polling."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.schemas import JobAccepted, JobRequest, JobStatus
from app.core.state import Job, enqueue, load

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
def submit(req: JobRequest) -> JobAccepted:
    job = Job(job_id=req.idempotency_id(), topic=req.topic, lang=req.lang, formats=req.formats)
    enqueue(job)                       # idempotente: mesmo payload -> mesmo job
    current = load(job.job_id) or job
    return JobAccepted(job_id=current.job_id, stage=current.stage)


@router.get("/{job_id}", response_model=JobStatus)
def get_status(job_id: str) -> JobStatus:
    job = load(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job não encontrado")
    return JobStatus(job_id=job.job_id, stage=job.stage, cost_brl=job.cost_brl,
                     error=job.error, artifacts=job.artifacts)

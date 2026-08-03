"""Enfileira o episódio piloto: terremoto da Venezuela (24/06/2026).

Uso: python scripts/enqueue_example.py
"""
from app.core.state import Job, enqueue
from app.api.schemas import JobRequest

req = JobRequest(
    topic="Terremoto doublet da Venezuela em 24/06/2026 (magnitudes 7,2 e 7,5, "
          "epicentro perto de San Felipe e Yumare): explicação geográfica do "
          "limite de placas Caribe/Sul-Americana e a cronologia dos 39 segundos.",
    lang="pt-BR",
    formats=["16:9", "9:16"],
)
job = Job(job_id=req.idempotency_id(), topic=req.topic, lang=req.lang, formats=req.formats)
enqueue(job)
print(f"enfileirado job_id={job.job_id}")

from pathlib import Path
from app.core.state import Job, enqueue
from app.api.schemas import JobRequest

topic = Path("prompts/ep01_topic.txt").read_text(encoding="utf-8").strip()
req = JobRequest(topic=topic, lang="pt-BR", formats=["16:9", "9:16"])
job = Job(job_id=req.idempotency_id(), topic=req.topic, lang=req.lang, formats=req.formats)
enqueue(job)
print(f"enfileirado job_id={job.job_id}")

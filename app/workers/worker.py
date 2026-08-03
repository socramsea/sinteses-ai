"""Worker: consome a fila Redis e roda o orquestrador. Polling, sem webhook."""
from __future__ import annotations

import logging

from app.core.state import Stage, load, next_job_id, save, set_stage
from app.logging_conf import setup_logging
from app.pipeline.orchestrator import run

setup_logging()
log = logging.getLogger("worker")


def main() -> None:
    log.info("worker Síntese iniciado — aguardando jobs")
    while True:
        job_id = next_job_id(timeout=5)
        if not job_id:
            continue
        job = load(job_id)
        if not job:
            continue
        try:
            run(job)
        except Exception as e:  # noqa: BLE001 — registra e marca FAILED
            log.exception("job %s falhou", job_id)
            job.error = f"{type(e).__name__}: {e}"
            set_stage(job, Stage.FAILED)
            save(job)


if __name__ == "__main__":
    main()

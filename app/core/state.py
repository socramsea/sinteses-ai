"""Máquina de estados do job, persistida em Redis.
Fluxo: QUEUED -> RESEARCHING -> SCRIPTING -> GENERATING -> NARRATING
       -> ASSEMBLING -> EXPORTING -> PUBLISHING -> DONE | FAILED
Idempotência: o job_id é derivado de um hash do payload (ver api.schemas),
então reenviar o mesmo pedido reusa o mesmo job em vez de gastar de novo.

Modo criativo (marketing): job.mode == "creative" carrega cenas prontas em
job.scenes e o orquestrador pula a pesquisa factual.
"""
from __future__ import annotations
import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
import redis
from app.config import settings

QUEUE_KEY = "sintese:queue"
JOB_PREFIX = "sintese:job:"
_r = redis.from_url(settings.redis_url, decode_responses=True)


class Stage(str, Enum):
    QUEUED = "QUEUED"
    RESEARCHING = "RESEARCHING"
    SCRIPTING = "SCRIPTING"
    GENERATING = "GENERATING"
    NARRATING = "NARRATING"
    ASSEMBLING = "ASSEMBLING"
    EXPORTING = "EXPORTING"
    PUBLISHING = "PUBLISHING"
    DONE = "DONE"
    FAILED = "FAILED"


@dataclass
class Job:
    job_id: str
    topic: str
    lang: str = "pt-BR"
    formats: list[str] = field(default_factory=lambda: ["16:9", "9:16"])
    # --- modo criativo (marketing) ---
    mode: str = "documentary"            # "documentary" | "creative"
    scenes: list | None = None           # cenas prontas (dicts) quando mode="creative"
    disclosure: bool = True              # mantém disclosure de IA
    # --- estado ---
    stage: str = Stage.QUEUED.value
    cost_brl: float = 0.0
    retries: int = 0
    error: str | None = None
    artifacts: dict = field(default_factory=dict)   # {script, scenes, clips, vo, exports}
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def key(self) -> str:
        return JOB_PREFIX + self.job_id


def save(job: Job) -> None:
    job.updated_at = time.time()
    _r.set(job.key(), json.dumps(asdict(job)))


def load(job_id: str) -> Job | None:
    raw = _r.get(JOB_PREFIX + job_id)
    if not raw:
        return None
    data = json.loads(raw)
    # tolera jobs antigos gravados antes dos campos novos
    allowed = Job.__dataclass_fields__.keys()
    data = {k: v for k, v in data.items() if k in allowed}
    return Job(**data)


def enqueue(job: Job) -> None:
    # idempotente: só cria se ainda não existe
    if not _r.exists(job.key()):
        save(job)
        _r.rpush(QUEUE_KEY, job.job_id)


def next_job_id(timeout: int = 5) -> str | None:
    res = _r.blpop(QUEUE_KEY, timeout=timeout)
    return res[1] if res else None


def set_stage(job: Job, stage: Stage) -> None:
    job.stage = stage.value
    save(job)

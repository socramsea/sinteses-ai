"""Cobertura da máquina de estados (app/core/state.py).

O Redis é trocado por um duplo em memória, então a suite roda num clone limpo
sem subir o compose — é o que garante que a persistência e a idempotência
descritas no README sejam verificáveis, não afirmações de confiança.
"""
from __future__ import annotations

import json

import pytest

from app.core import state
from app.core.state import Job, Stage


class FakeRedis:
    """Subconjunto do redis-py que state.py usa: set/get/exists/rpush/blpop."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}

    def set(self, key: str, value: str) -> None:
        self.store[key] = value

    def get(self, key: str):
        return self.store.get(key)

    def exists(self, key: str) -> int:
        return 1 if key in self.store else 0

    def rpush(self, key: str, value: str) -> None:
        self.lists.setdefault(key, []).append(value)

    def blpop(self, key: str, timeout: int = 0):
        items = self.lists.get(key) or []
        return (key, items.pop(0)) if items else None


@pytest.fixture
def r(monkeypatch) -> FakeRedis:
    fake = FakeRedis()
    monkeypatch.setattr(state, "_r", fake)
    return fake


def test_save_load_roundtrip(r):
    job = Job(job_id="abc123", topic="terremoto venezuela")
    job.cost_brl = 12.5
    job.artifacts = {"script": "spaces://sintese-media/abc123/script.json"}
    state.save(job)

    got = state.load("abc123")
    assert got is not None
    assert got.topic == "terremoto venezuela"
    assert got.cost_brl == 12.5
    assert got.artifacts == {"script": "spaces://sintese-media/abc123/script.json"}
    assert got.stage == Stage.QUEUED.value


def test_load_missing_returns_none(r):
    assert state.load("nao-existe") is None


def test_enqueue_persists_job_and_pushes_id(r):
    state.enqueue(Job(job_id="j1", topic="enchente rs"))

    assert state.load("j1") is not None
    assert r.lists[state.QUEUE_KEY] == ["j1"]


def test_enqueue_is_idempotent(r):
    """Reenviar o mesmo payload não pode enfileirar trabalho duplicado."""
    state.enqueue(Job(job_id="j1", topic="enchente rs"))
    state.enqueue(Job(job_id="j1", topic="enchente rs"))

    assert r.lists[state.QUEUE_KEY] == ["j1"]


def test_enqueue_nao_resseta_job_em_andamento(r):
    """O reenvio reusa o job existente em vez de zerar progresso e custo."""
    job = Job(job_id="j1", topic="enchente rs")
    state.enqueue(job)
    job.cost_brl = 48.0
    state.set_stage(job, Stage.GENERATING)

    state.enqueue(Job(job_id="j1", topic="enchente rs"))

    got = state.load("j1")
    assert got.stage == Stage.GENERATING.value
    assert got.cost_brl == 48.0


def test_set_stage_persiste_e_atualiza_timestamp(r):
    job = Job(job_id="j1", topic="x")
    state.save(job)
    antes = state.load("j1").updated_at

    state.set_stage(job, Stage.ASSEMBLING)

    got = state.load("j1")
    assert got.stage == Stage.ASSEMBLING.value
    assert got.updated_at >= antes


def test_load_tolera_campos_desconhecidos(r):
    """Job gravado por uma versão antiga do schema não pode quebrar o load."""
    r.set(
        state.JOB_PREFIX + "velho",
        json.dumps({"job_id": "velho", "topic": "t", "campo_extinto": True}),
    )

    got = state.load("velho")
    assert got is not None
    assert got.job_id == "velho"
    assert not hasattr(got, "campo_extinto")


def test_next_job_id_respeita_fifo(r):
    for jid in ("a", "b"):
        state.enqueue(Job(job_id=jid, topic=jid))

    assert state.next_job_id() == "a"
    assert state.next_job_id() == "b"
    assert state.next_job_id() is None


def test_modo_criativo_sobrevive_ao_roundtrip(r):
    """mode='creative' carrega cenas prontas; o worker depende disso ao recarregar."""
    cenas = [{"visual_prompt": "drone sobre a cidade", "dur_s": 4}]
    state.save(Job(job_id="c1", topic="brandfilm", mode="creative", scenes=cenas))

    got = state.load("c1")
    assert got.mode == "creative"
    assert got.scenes == cenas

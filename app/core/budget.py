"""Controle de custo. Custo é requisito, não detalhe (ADR-03 do RFC-001).

- teto por job (JOB_BUDGET_BRL_MAX)
- corta nº de cenas (JOB_MAX_SCENES) pra evitar runaway
- registra gasto incremental; aborta antes de chamar o provider se a próxima
  etapa projetar estouro.
"""
from __future__ import annotations

from app.config import settings
from app.core.errors import BudgetExceeded
from app.core.state import Job, save

# custo médio estimado por unidade (R$) — calibrar com a fatura real do fal.
COST_PER_CLIP_BRL = 6.0      # 1 cena image-to-video
COST_PER_RESEARCH_BRL = 1.5  # chamada anthropic (com cache reduz muito)


def guard_scene_count(n_scenes: int) -> int:
    return min(n_scenes, settings.job_max_scenes)


def charge(job: Job, amount_brl: float, reason: str) -> None:
    projected = job.cost_brl + amount_brl
    if projected > settings.job_budget_brl_max:
        raise BudgetExceeded(
            f"job {job.job_id}: {reason} levaria a R${projected:.2f} "
            f"(teto R${settings.job_budget_brl_max:.2f})"
        )
    job.cost_brl = projected
    save(job)


def estimate(n_scenes: int) -> float:
    return COST_PER_RESEARCH_BRL + guard_scene_count(n_scenes) * COST_PER_CLIP_BRL

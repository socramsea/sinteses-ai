"""Orquestrador: roda os estágios em ordem, com estado, custo e compliance.

QUEUED -> RESEARCHING -> SCRIPTING -> [compliance] -> GENERATING -> NARRATING
       -> ASSEMBLING -> EXPORTING -> (PUBLISHING) -> DONE

Suporta retomada: se o job já tem artifacts de estágios anteriores,
pula direto para onde parou.
"""
from __future__ import annotations

import logging

from app.config import settings
from app.core import budget
from app.core.state import Job, Stage, set_stage, save
from app.pipeline import assembly, compliance, export, geo, narration, research, scenes
from app.pipeline.video_provider import get_provider

log = logging.getLogger("orchestrator")
WORK = ".work"


def run(job: Job) -> None:
    # 1. pesquisa + roteiro (pula se já tiver script)
    if not job.artifacts.get("script"):
        set_stage(job, Stage.RESEARCHING)
        budget.charge(job, budget.COST_PER_RESEARCH_BRL, "pesquisa/roteiro")
        script = research.build_script(job.topic, job.lang)
        job.artifacts["script"] = script
        save(job)
    else:
        log.info("job %s: retomando — script já existe", job.job_id)
        script = job.artifacts["script"]

    # 2. plano de cenas + compliance (pula se já tiver compliance)
    scene_list = scenes.plan(script)
    if not job.artifacts.get("compliance"):
        set_stage(job, Stage.SCRIPTING)
        verdict = compliance.pre_generation_check(job.topic, script)
        job.artifacts["compliance"] = {"sensitive": verdict.sensitive, "notes": verdict.notes}
        save(job)

        # estima e valida orçamento antes de chamar o provider
        budget.charge(job, len(scene_list) * budget.COST_PER_CLIP_BRL, "geração de cenas")
    else:
        log.info("job %s: retomando — compliance já existe", job.job_id)
        # re-aplica charge se ainda não foi cobrado
        if job.cost_brl < budget.COST_PER_RESEARCH_BRL + len(scene_list) * budget.COST_PER_CLIP_BRL:
            budget.charge(job,
                          len(scene_list) * budget.COST_PER_CLIP_BRL - (job.cost_brl - budget.COST_PER_RESEARCH_BRL),
                          "geração de cenas (retomada)")

    # 3. geração de vídeo — retoma do último clip salvo
    clips: list[str] = list(job.artifacts.get("clips") or [])
    done_count = len(clips)
    if done_count < len(scene_list):
        set_stage(job, Stage.GENERATING)
        provider = get_provider()
        slug = script.get("slug", "topic")
        log.info("job %s: gerando clips %d..%d", job.job_id, done_count, len(scene_list) - 1)
        for sc in scene_list[done_count:]:
            if sc["kind"] == "geo":
                asset = geo.resolve_geo_asset(slug, sc["idx"])
                clips.append(asset if asset else
                             provider.generate(sc["prompt"], image_url=None,
                                               duration_s=sc["duration_s"],
                                               work_dir=f"{WORK}/{job.job_id}/clips"))
            else:
                clips.append(provider.generate(sc["prompt"], image_url=None,
                                               duration_s=sc["duration_s"],
                                               work_dir=f"{WORK}/{job.job_id}/clips"))
            job.artifacts["clips"] = clips  # checkpoint após cada clip
            save(job)
    else:
        log.info("job %s: retomando — todos os %d clips já gerados", job.job_id, len(clips))
        set_stage(job, Stage.GENERATING)

    job.artifacts["clips"] = clips

    # 4. narração (pula se já tiver vo)
    if not job.artifacts.get("vo"):
        set_stage(job, Stage.NARRATING)
        vo_text = " ".join(sc["narration"] for sc in scene_list if sc["narration"])
        vo_path = narration.narrate(vo_text, f"{WORK}/{job.job_id}/vo.mp3")
        job.artifacts["vo"] = vo_path
        save(job)
    else:
        log.info("job %s: retomando — narração já existe", job.job_id)
        vo_path = job.artifacts["vo"]

    # 5. montagem (pula se já tiver master)
    if not job.artifacts.get("master"):
        set_stage(job, Stage.ASSEMBLING)
        credits = [s.get("title", "") for s in script.get("sources", [])]
        master = assembly.assemble(clips, vo_path, credits, f"{WORK}/{job.job_id}/master.mp4")
        job.artifacts["master"] = master
        save(job)
    else:
        log.info("job %s: retomando — master já existe", job.job_id)
        master = job.artifacts["master"]

    # 6. export multi-formato
    set_stage(job, Stage.EXPORTING)
    job.artifacts["exports"] = export.export(master, job.formats, f"out/{job.job_id}")
    job.artifacts["platform_flags"] = compliance.platform_flags()

    set_stage(job, Stage.DONE)
    log.info("job %s DONE — custo R$%.2f", job.job_id, job.cost_brl)

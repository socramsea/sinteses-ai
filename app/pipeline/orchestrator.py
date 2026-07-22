"""Orquestrador: roda os estágios em ordem, com estado, custo e compliance.
QUEUED -> RESEARCHING -> SCRIPTING -> [compliance] -> GENERATING -> NARRATING
       -> ASSEMBLING -> EXPORTING -> (PUBLISHING) -> DONE
Suporta retomada: se o job já tem artifacts de estágios anteriores,
pula direto para onde parou.

Modo criativo (marketing): job.mode == "creative" desvia para _run_creative,
que pula pesquisa/fonte factual e usa job.scenes prontas. Mantém disclosure de IA.
"""
from __future__ import annotations
import logging
import re
from app.config import settings
from app.core import budget
from app.core.state import Job, Stage, set_stage, save
from app.pipeline import assembly, compliance, export, geo, narration, research, scenes
from app.pipeline.video_provider import get_provider

log = logging.getLogger("orchestrator")
WORK = ".work"


def _slugify(s: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return slug[:40] or "promo"


def run(job: Job) -> None:
    # desvio de marketing: cenas prontas, sem pesquisa factual
    if getattr(job, "mode", "documentary") == "creative":
        _run_creative(job)
        return

    # ===================== MODO DOCUMENTÁRIO (inalterado) =====================
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
        budget.charge(job, len(scene_list) * budget.COST_PER_CLIP_BRL, "geração de cenas")
    else:
        log.info("job %s: retomando — compliance já existe", job.job_id)
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
            job.artifacts["clips"] = clips
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


def _run_creative(job: Job) -> None:
    """Modo marketing: cenas prontas (job.scenes), sem pesquisa nem fonte factual.
    Mantém disclosure de IA. Reaproveita geração/narração/montagem/export."""
    log.info("job %s: MODO CRIATIVO (marketing)", job.job_id)

    # 1-2. roteiro sintético a partir das cenas prontas (sem research/fonte)
    if not job.artifacts.get("script"):
        set_stage(job, Stage.SCRIPTING)
        job.artifacts["script"] = {"slug": _slugify(job.topic), "sources": [], "creative": True}
        job.artifacts["compliance"] = {
            "sensitive": False,
            "notes": "modo criativo (marketing) — sem fonte factual; encenação permitida; disclosure de IA mantido",
        }
        save(job)
    script = job.artifacts["script"]

    # normaliza as cenas do job para o formato interno (dict com kind/idx/prompt/…)
    raw_scenes = job.scenes or []
    scene_list = []
    for i, sc in enumerate(raw_scenes):
        vp = sc.get("visual_prompt") if isinstance(sc, dict) else getattr(sc, "visual_prompt", "")
        du = (sc.get("duration_s") if isinstance(sc, dict) else getattr(sc, "duration_s", None)) or 2.0
        na = sc.get("narration") if isinstance(sc, dict) else getattr(sc, "narration", None)
        ov = sc.get("overlay") if isinstance(sc, dict) else getattr(sc, "overlay", None)
        scene_list.append({"kind": "creative", "idx": i, "prompt": vp,
                           "duration_s": du, "narration": na, "overlay": ov})
    if not scene_list:
        raise ValueError("mode='creative' exige job.scenes (nenhuma cena recebida)")

    # orçamento (cobra uma vez; respeita retomada)
    expected = len(scene_list) * budget.COST_PER_CLIP_BRL
    if job.cost_brl < expected:
        budget.charge(job, expected - job.cost_brl, "geração de cenas (criativo)")

    # 3. geração de vídeo — retoma do último clip salvo
    clips: list[str] = list(job.artifacts.get("clips") or [])
    if len(clips) < len(scene_list):
        set_stage(job, Stage.GENERATING)
        provider = get_provider()
        log.info("job %s: gerando clips %d..%d", job.job_id, len(clips), len(scene_list) - 1)
        for sc in scene_list[len(clips):]:
            clips.append(provider.generate(sc["prompt"], image_url=None,
                                           duration_s=sc["duration_s"],
                                           work_dir=f"{WORK}/{job.job_id}/clips"))
            job.artifacts["clips"] = clips
            save(job)
    else:
        set_stage(job, Stage.GENERATING)
    job.artifacts["clips"] = clips

    # 4. narração (opcional e NÃO-FATAL — hero é mudo; se edge-tts cair, segue sem áudio)
    if job.artifacts.get("vo") is None:
        set_stage(job, Stage.NARRATING)
        vo_text = " ".join(sc["narration"] for sc in scene_list if sc.get("narration"))
        vo_path = ""
        if vo_text.strip():
            try:
                vo_path = narration.narrate(vo_text, f"{WORK}/{job.job_id}/vo.mp3")
            except Exception as e:  # noqa: BLE001 — narração indisponível não derruba o promo
                log.warning("job %s: narração indisponível (%s) — seguindo SEM áudio",
                            job.job_id, type(e).__name__)
                vo_path = ""
        job.artifacts["vo"] = vo_path
        save(job)
    vo_path = job.artifacts.get("vo") or None

    # 5. montagem — sem créditos de fonte; overlays de UI/logo entram aqui (ver nota no roteiro)
    if not job.artifacts.get("master"):
        set_stage(job, Stage.ASSEMBLING)
        overlays = [sc.get("overlay") for sc in scene_list if sc.get("overlay")]
        job.artifacts["overlays"] = overlays  # assembly.py pode consumir isso para sobrepor a tela do app/logo
        master = assembly.assemble(clips, vo_path, [], f"{WORK}/{job.job_id}/master.mp4")
        job.artifacts["master"] = master
        save(job)
    master = job.artifacts["master"]

    # 6. export multi-formato + disclosure de IA
    set_stage(job, Stage.EXPORTING)
    job.artifacts["exports"] = export.export(master, job.formats, f"out/{job.job_id}")
    job.artifacts["platform_flags"] = compliance.platform_flags()
    set_stage(job, Stage.DONE)
    log.info("job %s DONE (criativo) — custo R$%.2f", job.job_id, job.cost_brl)

"""Filme do motor: B-roll de atenção e ofício (modo criativo, mudo).

São os 16 planos que saíram à mão no Playground da fal em 23/07/2026, agora pelo
pipeline. O motivo não é economia: é que o filme afirma que todo frame saiu deste
motor, e clipe feito na interface da fal não passou por ele. Rodando por aqui, a
afirmação vira verdade e os clipes entram no cache com o nome canônico
(`md5(url)[:12].mp4`, ver video_provider.py:85).

Uso:
    python -m scripts.enqueue_motor --dry-run    # lista os planos e o custo
    python -m scripts.enqueue_motor              # enfileira de verdade

Sem narração: a locução vem do MiniMax (prompts/vo_motor.txt) e a montagem segue
a voz, conforme docs/MONTAGEM-MOTOR.md.

CORREÇÃO DE PRESET
------------------
A rodada do Playground colou o ESTILO do filme das jubartes
(scripts/enqueue_filme_sea.py:8) nos 16 prompts — inclusive em "tela completamente
preta, nada mais" e em "sala escura, só as telas iluminam". "golden hour light,
crystal-clear turquoise ocean" contradizia 15 dos 16 planos.

Aqui só o LOOK é global. Luz, hora do dia e cenário vivem dentro de cada prompt,
porque são decisão de plano, não de filme. O plano 16 mostra a regra funcionando:
é o único que quer oceano em golden hour, e é o único que pede.
"""
from __future__ import annotations

import argparse

from app.api.schemas import JobRequest, Scene
from app.core import budget
from app.core.state import Job, enqueue

# Só a gramática de câmera e o acabamento. Nada de cenário, nada de hora do dia.
LOOK = ("National Geographic documentary style, stabilized camera, slow graceful "
        "motion, shallow depth of field, cinematic color grading, photorealistic, "
        "no text, no captions")

# (prompt, duração). Kling aceita 4/6/8s.
SHOTS: list[tuple[str, float]] = [
    ("Pure black frame slowly revealing faint grain and a single distant point of "
     "light, extremely slow fade up, nothing else", 8.0),
    ("Particles of light coalescing and dispersing over a dark background, like "
     "letters forming and dissolving, abstract, slow", 4.0),
    ("Rapid, almost strobing sequence of flickering light frames in warm golden "
     "tones over a dark background, abstract", 4.0),
    ("The glow of a screen dimming to total darkness, the light swallowed by "
     "black, slow and inevitable", 4.0),
    ("A projector beam switching on, cutting through dust in a dark room, the "
     "light settling into a steady warm cone", 4.0),
    ("An empty office at the end of the day, warm window light falling across the "
     "desks, slow lateral tracking move, no people", 8.0),
    ("An empty meeting room, cool morning light filtered through glass, chairs "
     "around a long table, static shot", 4.0),
    ("An empty stage under a single spotlight seen from the audience, dark "
     "auditorium, very slow camera push-in", 4.0),
    ("A blurred crowd in motion with one still figure in sharp focus among them, "
     "shallow depth of field", 6.0),
    ("The same crowd, focus racking to reveal the still figure clearly, slow "
     "focus pull", 4.0),
    ("Extreme close-up of a person's eyes watching something off-frame, light "
     "reflected in the pupils, subtle blink", 4.0),
    ("Close-up of calloused hands working, low warm light, face never visible, "
     "slow deliberate movement", 4.0),
    ("A city at night seen from above, thousands of lights, slow aerial drift, "
     "long-exposure feel", 6.0),
    ("Silhouette of a man from behind, seated before several glowing monitors in "
     "a dark room, only the screens lighting the scene, very slow push-in, face "
     "never visible", 8.0),
    ("An empty photo frame on a dark wooden surface, raking side light, dust "
     "motes floating, slow push-in", 4.0),
    # O único plano que realmente quer oceano em golden hour — e é o único que pede.
    ("Aerial drone shot over a crystal-clear turquoise ocean at golden hour, "
     "gentle waves, slow stabilized motion", 6.0),
]

TOPIC = "Sintese — filme do motor (B-roll de atencao e oficio)"
FORMATS = ["16:9", "9:16"]


def build() -> tuple[JobRequest, list[dict]]:
    req = JobRequest(
        topic=TOPIC,
        lang="pt-BR",
        formats=FORMATS,
        mode="creative",
        scenes=[Scene(visual_prompt=f"{p}, {LOOK}", duration_s=d) for p, d in SHOTS],
        disclosure=True,
    )
    return req, [s.model_dump() for s in req.scenes]


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Enfileira o B-roll do filme do motor (modo criativo).")
    ap.add_argument("--dry-run", action="store_true",
                    help="lista os planos e o custo estimado sem enfileirar")
    args = ap.parse_args()

    req, scene_dicts = build()
    cap = budget.settings.job_max_scenes
    gerados = min(len(SHOTS), cap)
    estimado = gerados * budget.COST_PER_CLIP_BRL

    def aviso_cap() -> None:
        if len(SHOTS) > cap:
            print(f"\nATENCAO: {len(SHOTS)} planos, mas JOB_MAX_SCENES={cap}. "
                  f"O motor corta para {cap} e os ultimos {len(SHOTS) - cap} "
                  f"NAO serao gerados.\nSuba JOB_MAX_SCENES no .env para "
                  f"{len(SHOTS)} se quiser o filme inteiro.")

    if args.dry_run:
        for i, (p, d) in enumerate(SHOTS):
            marca = "  " if i < cap else "X "
            print(f"{marca}{i:2d}  {d:.0f}s  {p[:70]}")
        print(f"\n{gerados} de {len(SHOTS)} planos · estimativa R${estimado:.2f} "
              f"(R${budget.COST_PER_CLIP_BRL:.2f}/clipe, valor NAO calibrado — "
              f"kling v3 pro e mais caro que isso)")
        print(f"teto por job: R${budget.settings.job_budget_brl_max:.2f}")
        print(f"job_id que seria criado: {req.idempotency_id()}")
        aviso_cap()
        return

    job = Job(job_id=req.idempotency_id(), topic=req.topic, lang=req.lang,
              formats=req.formats, mode=req.mode, scenes=scene_dicts,
              disclosure=req.disclosure)
    enqueue(job)
    print(f"enfileirado job_id={job.job_id} · {gerados} de {len(SHOTS)} planos · "
          f"estimativa R${estimado:.2f}")
    aviso_cap()


if __name__ == "__main__":
    main()

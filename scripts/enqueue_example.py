"""Enfileira o episódio piloto: terremoto da Venezuela (24/06/2026).

Uso:
    python scripts/enqueue_example.py                # pt-BR (padrão)
    python scripts/enqueue_example.py --lang en      # inglês
    python scripts/enqueue_example.py --both         # os dois

O job_id é hash do payload e inclui o idioma, então pt-BR e en viram dois jobs
independentes: o mesmo evento rende as duas versões sem colidir na fila, e cada
uma pode ser retomada por conta própria.
"""
from __future__ import annotations

import argparse

from app.api.schemas import JobRequest
from app.core.state import Job, enqueue

TOPICS = {
    "pt-BR": (
        "Terremoto doublet da Venezuela em 24/06/2026 (magnitudes 7,2 e 7,5, "
        "epicentro perto de San Felipe e Yumare): explicação geográfica do "
        "limite de placas Caribe/Sul-Americana e a cronologia dos 39 segundos."
    ),
    "en": (
        "The 24 June 2026 Venezuela doublet earthquake (magnitudes 7.2 and 7.5, "
        "epicentre near San Felipe and Yumare): a geographic explanation of the "
        "Caribbean/South American plate boundary and the 39-second timeline."
    ),
}
FORMATS = ["16:9", "9:16"]


def submit(lang: str) -> str:
    req = JobRequest(topic=TOPICS[lang], lang=lang, formats=FORMATS)
    job = Job(job_id=req.idempotency_id(), topic=req.topic,
              lang=req.lang, formats=req.formats)
    enqueue(job)
    return job.job_id


def main() -> None:
    p = argparse.ArgumentParser(
        description="Enfileira o piloto da Venezuela em pt-BR e/ou inglês.")
    p.add_argument("--lang", choices=sorted(TOPICS), default="pt-BR",
                   help="idioma do job (padrão: pt-BR)")
    p.add_argument("--both", action="store_true",
                   help="enfileira pt-BR e en de uma vez")
    args = p.parse_args()

    for lang in (sorted(TOPICS) if args.both else [args.lang]):
        print(f"enfileirado lang={lang} job_id={submit(lang)}")


if __name__ == "__main__":
    main()

"""Gera todos os segmentos de VO de um roteiro no formato id|voz|texto.

Uso:
    python -m scripts.generate_vo_lote                       # brandfilm (padrão)
    python -m scripts.generate_vo_lote --roteiro prompts/vo_motor.txt \
                                       --out out/motor-vo

Idempotente: pula segmentos que já existem no destino, então reexecutar depois de
uma falha não regera — nem recobra — o que já saiu.
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

VOZES = {
    "NARRADORA": "Voice6d64b7cc1784772153",
    "CETICA": "Voice43759aae1784770778",
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--roteiro", default="prompts/vo_brandfilm.txt",
                    help="arquivo id|voz|texto (padrão: prompts/vo_brandfilm.txt)")
    ap.add_argument("--out", default="out/brandfilm-vo",
                    help="destino dos mp3 (padrão: out/brandfilm-vo)")
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    linhas = pathlib.Path(args.roteiro).read_text().splitlines()
    for ln in linhas:
        if not ln or ln.startswith("#"):
            continue
        sid, voz, texto = ln.split("|", 2)
        destino = out / f"{sid}.mp3"
        if destino.exists():
            print(f"[skip] {sid} ja existe")
            continue
        vid = VOZES.get(voz)
        if not vid or "PREENCHER" in vid:
            print(f"[pulo] {sid}: voz {voz} sem ID ainda")
            continue
        print(f"[gera] {sid} ({voz})")
        r = subprocess.run([sys.executable, "-m", "scripts.generate_vo",
                            texto, "--voice", vid, "--name", sid,
                            "--out", str(out)])
        if r.returncode != 0:
            raise SystemExit(f"falhou em {sid} — parando para nao gastar as cegas")


if __name__ == "__main__":
    main()

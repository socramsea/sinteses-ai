"""Gera todos os segmentos de VO do brandfilm a partir de prompts/vo_brandfilm.txt.
Uso: python -m scripts.generate_vo_lote
Idempotente: pula segmentos que ja existem em out/brandfilm-vo/.
"""
import pathlib, subprocess, sys

VOZES = {
    "NARRADORA": "ttv-voice-2026071206495226-C7J1gp7Q",
    "CETICA": "PREENCHER_APOS_RESGATE",
}
OUT = pathlib.Path("out/brandfilm-vo")

def main() -> None:
    linhas = pathlib.Path("prompts/vo_brandfilm.txt").read_text().splitlines()
    for ln in linhas:
        if not ln or ln.startswith("#"):
            continue
        sid, voz, texto = ln.split("|", 2)
        destino = OUT / f"{sid}.mp3"
        if destino.exists():
            print(f"[skip] {sid} ja existe")
            continue
        vid = VOZES[voz]
        if "PREENCHER" in vid:
            print(f"[pulo] {sid}: voz {voz} sem ID ainda")
            continue
        print(f"[gera] {sid} ({voz})")
        r = subprocess.run([sys.executable, "-m", "scripts.generate_vo",
                            texto, "--voice", vid, "--name", sid])
        if r.returncode != 0:
            raise SystemExit(f"falhou em {sid} — parando para nao gastar as cegas")

if __name__ == "__main__":
    main()

"""Gera leito de trilha via stable-audio no fal.ai.

Uso:
    python -m scripts.generate_trilha --seconds 94 --name motor
    python -m scripts.generate_trilha --seconds 94 --name motor --dry-run

Mesmo padrao de fila do generate_vo.py (submit -> poll -> download). O payload
do stable-audio nao esta documentado neste repo: em caso de 422 o corpo do erro
e impresso inteiro, que e onde o fal lista os campos esperados. Submit invalido
e rejeitado antes de gerar, entao errar o nome do campo nao custa credito.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import time
import urllib.error
import urllib.request

MODEL = "fal-ai/stable-audio-25/text-to-audio"

PROMPT_PADRAO = (
    "Cinematic documentary underscore. Sparse piano and low sustained strings, "
    "slow patient build, restrained and quietly tense, warm dark tone. No drums, "
    "no percussion, no vocals. Leaves space for a narrator: nothing busy in the "
    "mid range. Single subtle swell near the end, then settles."
)


def _req(url: str, key: str, data: dict | None = None) -> dict:
    r = urllib.request.Request(url, headers={
        "Authorization": f"Key {key}", "Content-Type": "application/json"})
    if data is not None:
        r.data = json.dumps(data).encode()
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        corpo = e.read().decode(errors="replace")
        print(f"\nHTTP {e.code} em {url}\n{corpo}\n")
        raise SystemExit(
            "submit rejeitado — nenhum credito gasto. Ajuste o payload conforme "
            "os campos listados acima.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Gera leito de trilha no fal.")
    ap.add_argument("--seconds", type=float, required=True, help="duracao alvo")
    ap.add_argument("--name", required=True, help="nome do arquivo de saida")
    ap.add_argument("--prompt", default=PROMPT_PADRAO)
    ap.add_argument("--out", default="out/trilhas")
    ap.add_argument("--dry-run", action="store_true",
                    help="mostra o payload e sai, sem chamar a fal")
    args = ap.parse_args()

    payload = {"prompt": args.prompt, "seconds_total": args.seconds}

    if args.dry_run:
        print(f"POST https://queue.fal.run/{MODEL}")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    key = os.environ["FAL_KEY"]
    sub = _req(f"https://queue.fal.run/{MODEL}", key, payload)

    while True:
        st = _req(sub["status_url"], key)
        if st.get("status") == "COMPLETED":
            break
        if st.get("status") in ("FAILED", "ERROR"):
            raise SystemExit(f"falhou: {json.dumps(st)[:400]}")
        time.sleep(3)

    res = _req(sub["response_url"], key)
    audio = res.get("audio") or {}
    url = audio.get("url") if isinstance(audio, dict) else audio
    if not url:
        raise SystemExit(f"sem URL de audio: {json.dumps(res)[:400]}")

    outdir = pathlib.Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    # o stable-audio devolve WAV; nao chumbar .mp3 ou o arquivo mente sobre si
    ext = pathlib.Path(url.split("?")[0]).suffix or ".wav"
    destino = outdir / f"trilha-{args.name}{ext}"
    with urllib.request.urlopen(url, timeout=300) as resp:
        destino.write_bytes(resp.read())
    print(f"trilha salva em: {destino}")


if __name__ == "__main__":
    main()

"""Baixa os 16 clipes do B-roll do motor pelos request_id da fila da fal.

Eles foram gerados em 23/07/2026 no Playground e já estão pagos. Baixar é a
alternativa barata a regerar: mesmo material, custo zero.

Uso:
    python -m scripts.baixar_clipes_fal --probe 0    # testa 1 id, mostra o JSON cru
    python -m scripts.baixar_clipes_fal              # baixa os 16
    python -m scripts.baixar_clipes_fal --out .work/motor-broll

Reaproveita `FalProvider._extract_url` e `_download`, então cada arquivo cai com
o nome canônico do cache (`md5(url)[:12].mp4`) e herda o retry de download.
Idempotente: o que já está no manifesto e existe em disco é pulado.

SOBRE O CAMINHO DA API
----------------------
O `video_provider.py` documenta que "o caminho de status do fal usa só o prefixo
base do modelo, não o slug completo". Por isso `--model-base` é `fal-ai/kling-video`
e não `fal-ai/kling-video/v3/pro/text-to-video`.

Esse caminho de consulta por request_id foi INFERIDO daquele comentário — o código
do repo nunca o exercita, porque no fluxo normal a URL vem pronta no submit. Rode
`--probe` antes dos 16: ele imprime a URL chamada e a resposta crua.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx

from app.config import settings
from app.pipeline.video_provider import FAL_BASE, FalProvider

MODEL_BASE = "fal-ai/kling-video"

# (slug, request_id) na ordem de SHOTS em scripts/enqueue_motor.py
CLIPES: list[tuple[str, str]] = [
    ("black-ponto-de-luz",    "019f915d-7455-7a92-9c6f-6a6f896a0a8c"),
    ("particulas-de-luz",     "019f9161-ca3c-7c70-8e34-6877e673146d"),
    ("estroboscopio-dourado", "019f915f-c518-7c50-ab9b-2190ce255b60"),
    ("tela-apagando",         "019f9163-409c-75b3-9dba-f798520b2a1e"),
    ("feixe-de-projetor",     "019f9164-e514-78b2-8e0a-c8df7bfd32af"),
    ("escritorio-vazio",      "019f9152-24ec-7d71-9b2f-e44c0d7b0018"),
    ("sala-de-reuniao-vazia", "019f9159-4a72-7e81-8329-6521c721d630"),
    ("palco-vazio",           "019f9157-c237-78d1-849e-2d19006534db"),
    ("multidao-desfocada",    "019f9155-19f6-72d3-b4d5-fb1e782bbf01"),
    ("multidao-foco-revela",  "019f9156-6313-7c01-bf95-33a991601ef0"),
    ("olhos-close",           "019f915a-b034-7c82-94b9-915c7595960e"),
    ("maos-calejadas",        "019f9150-2d6e-7b21-a6e9-bd53b743034f"),
    ("cidade-a-noite",        "019f915b-e420-7602-9049-0c693bbc0a8e"),
    ("silhueta-monitores",    "019f914c-9e64-7043-b924-c19e08712e6f"),
    ("moldura-vazia",         "019f914b-2760-7793-822d-bc1e192385d7"),
    ("drone-oceano",          "019f914e-c9ba-7733-b06c-3ff89b60811b"),
]


def _headers() -> dict:
    if not settings.fal_key:
        raise SystemExit("FAL_KEY ausente — preencha o .env")
    return {"Authorization": f"Key {settings.fal_key}"}


def _result_url(model_base: str, request_id: str) -> str:
    return f"{FAL_BASE}/{model_base}/requests/{request_id}"


def _fetch(model_base: str, request_id: str) -> dict:
    url = _result_url(model_base, request_id)
    with httpx.Client(timeout=60) as c:
        r = c.get(url, headers=_headers())
        r.raise_for_status()
        return r.json()


def probe(idx: int, model_base: str) -> None:
    slug, rid = CLIPES[idx]
    url = _result_url(model_base, rid)
    print(f"slug   : {slug}")
    print(f"GET    : {url}\n")
    try:
        out = _fetch(model_base, rid)
    except httpx.HTTPStatusError as e:
        print(f"HTTP {e.response.status_code}: {e.response.text[:500]}")
        print("\nSe deu 404, o prefixo do modelo esta errado. Tente --model-base "
              "com outro recorte do slug (ex.: fal-ai/kling-video/v3).")
        raise SystemExit(1)
    print(json.dumps(out, indent=2, ensure_ascii=False)[:1500])
    print(f"\nURL extraida: {FalProvider._extract_url(out)}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Baixa os clipes ja gerados na fal pelos request_id.")
    ap.add_argument("--out", default=".work/motor-broll", help="pasta de destino")
    ap.add_argument("--model-base", default=MODEL_BASE,
                    help=f"prefixo base do modelo (padrao: {MODEL_BASE})")
    ap.add_argument("--probe", type=int, metavar="IDX",
                    help="consulta so o indice IDX e imprime a resposta crua")
    args = ap.parse_args()

    if args.probe is not None:
        probe(args.probe, args.model_base)
        return

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifesto_path = out_dir / "manifest.json"
    manifesto: dict = {}
    if manifesto_path.exists():
        manifesto = json.loads(manifesto_path.read_text())

    for i, (slug, rid) in enumerate(CLIPES):
        anterior = manifesto.get(slug)
        if anterior and Path(anterior["path"]).exists():
            print(f"[skip] {i:2d} {slug}")
            continue
        print(f"[baixa] {i:2d} {slug}")
        try:
            out = _fetch(args.model_base, rid)
            url = FalProvider._extract_url(out)
            path = FalProvider._download(url, str(out_dir))
        except Exception as e:  # noqa: BLE001 — um id ruim nao derruba os outros
            print(f"        FALHOU: {type(e).__name__}: {e}")
            continue
        manifesto[slug] = {"request_id": rid, "url": url, "path": path}
        manifesto_path.write_text(json.dumps(manifesto, indent=2, ensure_ascii=False))

    print(f"\n{len(manifesto)}/{len(CLIPES)} em {out_dir}")
    print(f"manifesto: {manifesto_path}")


if __name__ == "__main__":
    main()

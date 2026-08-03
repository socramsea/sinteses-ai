"""Modo clipe: gera um take avulso direto no provider, sem pipeline completo.

Uso:
  python scripts/generate_clip.py "prompt em ingles" --dur 8 --out video-final/sea-baleias
"""
import argparse

from app.pipeline.video_provider import get_provider


def main() -> None:
    ap = argparse.ArgumentParser(description="Gera clipe avulso via fal.ai")
    ap.add_argument("prompt", help="prompt visual em ingles")
    ap.add_argument("--dur", type=float, default=8, help="duracao em segundos (Kling: 4/6/8)")
    ap.add_argument("--out", default=".work/clips", help="pasta de saida")
    args = ap.parse_args()

    provider = get_provider()
    path = provider.generate(
        prompt=args.prompt,
        image_url=None,
        duration_s=args.dur,
        work_dir=args.out,
    )
    print(f"clipe salvo em: {path}")


if __name__ == "__main__":
    main()

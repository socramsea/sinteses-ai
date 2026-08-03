"""Teste do LTX-2.3 Reframe: converte um clipe 16:9 em 9:16 sem crop destrutivo.
Uso: docker compose run --rm worker python -m scripts.reframe_clip URL_DO_VIDEO
"""
import sys

from app.pipeline.video_provider import FalProvider

MODEL = "fal-ai/ltx-2.3/reframe"

def main() -> None:
    video_url = sys.argv[1]
    aspecto = sys.argv[2] if len(sys.argv) > 2 else "9:16"
    p = FalProvider()
    payload = {"video_url": video_url, "aspect_ratio": aspecto}
    print(f"submetendo reframe {aspecto}...")
    sub = p._submit(MODEL, payload)
    url = p._poll(sub["status_url"], sub["response_url"])
    path = p._download(url, "video-final/reframe-teste")
    print(f"reframe salvo em: {path}")

if __name__ == "__main__":
    main()

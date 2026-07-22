"""Gera voice-over via MiniMax speech-02-hd no fal.ai (voz desenhada, PT-BR).
Uso: python -m scripts.generate_vo "texto <#1.0#> com pausas" --voice VOICE_ID --name freeze1
"""
import argparse, os, time, json, pathlib
import urllib.request

MODEL = "fal-ai/minimax/speech-02-hd"

def _req(url, key, data=None):
    r = urllib.request.Request(url, headers={
        "Authorization": f"Key {key}", "Content-Type": "application/json"})
    if data is not None:
        r.data = json.dumps(data).encode()
    with urllib.request.urlopen(r, timeout=120) as resp:
        return json.loads(resp.read().decode())

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("text")
    ap.add_argument("--voice", required=True)
    ap.add_argument("--speed", type=float, default=0.9)
    ap.add_argument("--emotion", default="neutral")
    ap.add_argument("--out", default="out/brandfilm-vo")
    ap.add_argument("--name", default=None)
    args = ap.parse_args()

    key = os.environ["FAL_KEY"]
    payload = {"text": args.text,
               "voice_setting": {"voice_id": args.voice,
                                  "speed": args.speed,
                                  "emotion": args.emotion}}

    sub = _req(f"https://queue.fal.run/{MODEL}", key, payload)

    while True:
        st = _req(sub["status_url"], key)
        if st.get("status") == "COMPLETED":
            break
        if st.get("status") in ("FAILED", "ERROR"):
            raise SystemExit(f"falhou: {json.dumps(st)[:400]}")
        time.sleep(2)

    res = _req(sub["response_url"], key)
    audio = res.get("audio") or {}
    url = audio.get("url") if isinstance(audio, dict) else audio
    if not url:
        raise SystemExit(f"sem URL de audio: {json.dumps(res)[:400]}")

    outdir = pathlib.Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
    name = args.name or f"vo-{int(time.time())}"
    path = outdir / f"{name}.mp3"
    with urllib.request.urlopen(url, timeout=180) as resp:
        path.write_bytes(resp.read())
    print(f"vo salvo em: {path}")

if __name__ == "__main__":
    main()

"""Renderiza um cue sheet (out/motor-cue.json) em master de video.

Uso:
    python -m scripts.render_cue --until 20        # so os 20s iniciais, pra validar
    python -m scripts.render_cue                   # filme inteiro
    python -m scripts.render_cue --sem-audio       # so imagem, render rapido

Consome o JSON gerado por scripts.cue_motor. Nao passa por app/pipeline/assembly
nem export: aqueles assumem master 16:9 e concatenacao simples, e este filme e
9:16 com linha de tempo (freeze, slow, VO posicionado, trilha mixada).

Se o corte provar valor, este modulo e o candidato a virar app/pipeline/timeline.py.
"""
from __future__ import annotations

import argparse
import json
import pathlib

FONTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONTE_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
ZOOM_FREEZE = 0.04          # 4% ao longo do freeze; parado demais parece travamento


def db_para_fator(db: float) -> float:
    return 10.0 ** (db / 20.0)


def _pedaco(cue: dict, w: int, h: int):
    """Um cue -> um clipe de video normalizado em w x h."""
    from moviepy import VideoFileClip, vfx

    src = VideoFileClip(cue["src"])
    if cue["fx"] == "freeze":
        t = min(cue["in"], max(src.duration - 0.02, 0.0))
        peca = src.to_ImageClip(t).with_duration(cue["dur"]).resized((w, h))
        # zoom lento durante o freeze, depois corta de volta ao quadro
        d = cue["dur"]
        # o excedente do zoom e cortado pelo CompositeVideoClip via with_position
        peca = peca.resized(lambda tt, d=d: 1.0 + ZOOM_FREEZE * (tt / d))
        return peca, True
    peca = src.subclipped(cue["in"], cue["in"] + cue["src_dur"]).resized((w, h))
    if cue["rate"] != 1.0:
        peca = peca.with_effects([vfx.MultiplySpeed(cue["rate"])])
    return peca, False


def montar_video(cue_sheet: dict):
    """Monta o filme inteiro. Recortar janela e trabalho do subclipped no fim —
    filtrar cues aqui daria linha de tempo diferente da definitiva, e teste que
    nao exercita o material final nao serve de teste."""
    from moviepy import CompositeVideoClip, vfx

    w, h = cue_sheet["master"]["w"], cue_sheet["master"]["h"]
    xfade = cue_sheet.get("crossfade", 0.0)
    camadas, anterior_clip = [], None

    anterior = None          # (peca, cue) do corte anterior, para a cauda do dissolve

    for cue in cue_sheet["video"]:
        peca, e_freeze = _pedaco(cue, w, h)
        # dissolve so entre clipes DIFERENTES: entre um plano e seu proprio freeze,
        # um crossfade dissolveria a imagem em si mesma
        troca_de_clipe = anterior_clip is not None and cue["clip"] != anterior_clip

        if troca_de_clipe and xfade > 0:
            peca = peca.with_effects([vfx.CrossFadeIn(xfade)])
            # dissolve REAL: o plano que sai ganha uma cauda de ultimo quadro
            # congelado sob o que entra. Sem isso o CrossFadeIn sobe a partir do
            # preto do composite e o filme escurece em cada troca.
            peca_ant, cue_ant = anterior
            cauda = (peca_ant.to_ImageClip(max(peca_ant.duration - 0.02, 0))
                     .with_duration(xfade)
                     .with_start(cue["at"])
                     .with_effects([vfx.CrossFadeOut(xfade)]))
            camadas.append(cauda.with_position("center"))

        peca = peca.with_start(cue["at"])
        if e_freeze:
            peca = peca.with_position("center")
        camadas.append(peca)
        anterior, anterior_clip = (peca, cue), cue["clip"]

    fim = cue_sheet["duration"]
    video = CompositeVideoClip(camadas, size=(w, h)).with_duration(fim)
    return video.with_effects([vfx.FadeIn(1.2)])


def montar_audio(cue_sheet: dict):
    from moviepy import AudioFileClip, CompositeAudioClip, afx

    fim = cue_sheet["duration"]
    faixas = []

    for seg in cue_sheet["vo"]:
        vo = AudioFileClip(seg["src"]).with_start(seg["at"])
        faixas.append(vo)

    leito_spec = cue_sheet.get("bed") or {}
    caminho = leito_spec.get("src")
    if caminho and pathlib.Path(caminho).exists():
        leito = AudioFileClip(caminho)
        if leito.duration > fim:
            leito = leito.subclipped(0, fim)
        efeitos = [afx.MultiplyVolume(db_para_fator(leito_spec.get("gain_db", -17)))]
        for d in leito_spec.get("duck", []):
            if d["at"] < fim:
                efeitos.append(afx.MultiplyVolume(
                    db_para_fator(d["gain_db"] - leito_spec.get("gain_db", -17)),
                    start_time=d["at"], end_time=min(d["at"] + d["dur"], fim)))
        fade = leito_spec.get("fade_out", 0)
        if fade:
            efeitos.append(afx.AudioFadeOut(fade))
        faixas.append(leito.with_effects(efeitos))

    return CompositeAudioClip(faixas).with_duration(fim) if faixas else None


def sobrepor_disclosure(video, cue_sheet: dict):
    """Disclosure de IA persistente — o proprio filme exige isso na s07."""
    from moviepy import ColorClip, CompositeVideoClip, TextClip

    texto = cue_sheet.get("disclosure")
    if not texto:
        return video
    w, h, d = video.w, video.h, video.duration
    # 36px, nao 26: em 9:16 o filme e assistido no celular, com a barra do
    # sistema competindo pelo rodape
    txt = TextClip(text=texto, font=FONTE, font_size=36, color="white", duration=d)
    faixa = ColorClip(size=(w, 74), color=(0, 0, 0), duration=d).with_opacity(0.5)
    grupo = CompositeVideoClip(
        [faixa, txt.with_position(("center", "center"))], size=(w, 74)
    ).with_duration(d).with_position(("center", h - 120))
    return CompositeVideoClip([video, grupo], size=(w, h)).with_duration(d)


def sobrepor_cartao(video, cue_sheet: dict):
    from moviepy import ColorClip, CompositeVideoClip, TextClip

    cartao = cue_sheet.get("card")
    if not cartao:
        return video
    w, h, dur = video.w, video.h, cartao["dur"]
    preto = ColorClip(size=(w, h), color=(0, 0, 0), duration=dur).with_opacity(0.82)
    linhas = []
    y = h / 2 - 70
    for i, linha in enumerate(cartao["lines"]):
        tc = TextClip(text=linha, font=FONTE_BOLD if i == 0 else FONTE,
                      font_size=64 if i == 0 else 34, color="white", duration=dur)
        linhas.append(tc.with_position(("center", y)))
        y += 110 if i == 0 else 60
    grupo = CompositeVideoClip([preto, *linhas], size=(w, h)).with_duration(dur)
    from moviepy import vfx
    grupo = grupo.with_effects([vfx.CrossFadeIn(cartao.get("fade_from_black", 1.0))])
    grupo = grupo.with_start(cartao["at"])
    return CompositeVideoClip([video, grupo], size=(w, h)).with_duration(video.duration)


def main() -> None:
    ap = argparse.ArgumentParser(description="Renderiza o cue sheet em video.")
    ap.add_argument("--cue", default="out/motor-cue.json")
    ap.add_argument("--out", default="out/motor/filme-motor-9x16.mp4")
    ap.add_argument("--from", type=float, default=0.0, dest="inicio",
                    help="renderiza a partir de N segundos")
    ap.add_argument("--until", type=float, help="renderiza ate N segundos")
    ap.add_argument("--sem-audio", action="store_true", dest="sem_audio")
    args = ap.parse_args()

    cue_sheet = json.loads(pathlib.Path(args.cue).read_text())
    total = cue_sheet["duration"]
    fim = min(args.until, total) if args.until is not None else total
    if args.inicio >= fim:
        raise SystemExit(f"--from {args.inicio} nao e menor que o fim {fim}")
    print(f"renderizando {args.inicio:.2f}s..{fim:.2f}s de {total:.2f}s "
          f"({cue_sheet['master']['w']}x{cue_sheet['master']['h']} "
          f"@ {cue_sheet['master']['fps']}fps)")

    video = montar_video(cue_sheet)
    video = sobrepor_disclosure(video, cue_sheet)
    video = sobrepor_cartao(video, cue_sheet)

    audio = None if args.sem_audio else montar_audio(cue_sheet)
    if audio is not None:
        video = video.with_audio(audio)

    # a janela e recortada do filme completo: o trecho testado e identico ao
    # que sairia no render definitivo
    if args.inicio > 0 or fim < total:
        video = video.subclipped(args.inicio, fim)

    destino = pathlib.Path(args.out)
    destino.parent.mkdir(parents=True, exist_ok=True)
    bruto = destino.with_name(destino.stem + "-bruto" + destino.suffix)
    video.write_videofile(
        str(bruto), fps=cue_sheet["master"]["fps"], codec="libx264",
        audio=audio is not None, audio_codec="aac" if audio is not None else None,
        preset="medium", threads=4,
    )

    if audio is None:
        bruto.rename(destino)
        print(f"master: {destino}")
        return

    # Loudness em segunda passada: o moviepy nao expoe loudnorm, e sem isso a
    # mixagem sai baixa demais para vertical social. Video e copiado, nao
    # recodificado — so o audio e reprocessado.
    import subprocess
    r = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(bruto),
         "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(destino)],
        capture_output=True, text=True)
    if r.returncode != 0:
        print(f"loudnorm falhou, mantendo o bruto:\n{r.stderr[:400]}")
        bruto.rename(destino)
    else:
        bruto.unlink()
    print(f"master: {destino}")


if __name__ == "__main__":
    main()

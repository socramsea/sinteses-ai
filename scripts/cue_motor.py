"""Gera o cue sheet do filme do motor a partir da decupagem de docs/MONTAGEM-MOTOR.md.

Uso:
    python -m scripts.cue_motor                      # escreve out/motor-cue.json
    python -m scripts.cue_motor --print              # imprime a linha de tempo

Por que gerar em vez de escrever o JSON na mao: os timecodes derivam das duracoes
REAIS do VO (medidas por ffprobe) e das duracoes reais dos clipes. Escrito a mao,
qualquer regeracao de VO desalinharia o filme em silencio. Aqui o script VALIDA:
se a soma dos cortes nao fechar com a linha de tempo da voz, ele recusa.

Modelo de cue — um so, uniforme:
    rate == 1.0  -> velocidade normal, saida = src_dur
    rate == 0.5  -> slow 50%,          saida = src_dur / rate
    rate == 0    -> freeze no instante `in`, saida = out_dur explicito
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess

VO_DIR = pathlib.Path("out/motor-vo")
BROLL_MANIFEST = pathlib.Path(".work/motor-broll/manifest.json")
TRILHA = pathlib.Path("out/trilhas/trilha-motor.wav")
SAIDA = pathlib.Path("out/motor-cue.json")

ABERTURA_SILENCIOSA = 12.0
SEGMENTOS = ["s01", "s02", "s03", "s04", "s05", "s06", "s07", "s08"]

MASTER = {"w": 1080, "h": 1920, "fps": 24}

# Crossfade curto de proposito: a regra "3-4s" do MONTAGEM.md nasceu num filme de
# clipes de 8s. Aqui o material tem 4-5s — 3s de crossfade comeria o plano inteiro.
CROSSFADE = 0.6

DISCLOSURE = "Cenas recriadas por IA · imagens ilustrativas"
CARTAO = ["Síntese", "github.com/socramsea/sinteses-ai"]

# (slug, in, src_dur, rate, out_dur_se_freeze)
SEQ: list[tuple[str, float, float, float, float | None]] = [
    # abertura silenciosa + s01 + s02
    ("black-ponto-de-luz",    0.00, 6.00, 1.0, None),
    ("estroboscopio-dourado", 0.00, 4.00, 1.0, None),
    ("tela-apagando",         0.00, 5.00, 1.0, None),
    ("particulas-de-luz",     0.00, 4.00, 1.0, None),
    ("feixe-de-projetor",     0.00, 4.00, 1.0, None),
    ("silhueta-monitores",    0.00, 7.90, 1.0, None),
    ("silhueta-monitores",    7.90, 0.00, 0.0, 0.76),   # freeze em "Síntese"
    # s03
    ("maos-calejadas",        0.00, 4.00, 1.0, None),
    ("sala-de-reuniao-vazia", 0.00, 4.00, 1.0, None),
    ("escritorio-vazio",      0.00, 6.83, 1.0, None),
    # s04 — a pergunta da CETICA congela a imagem
    ("escritorio-vazio",      6.83, 0.00, 0.0, 2.84),
    # s05
    ("multidao-desfocada",    0.00, 5.00, 1.0, None),
    ("multidao-foco-revela",  0.00, 4.00, 1.0, None),
    ("olhos-close",           0.00, 2.00, 1.0, None),
    ("olhos-close",           2.00, 2.00, 0.5, None),   # slow 50% -> 4.00s
    ("olhos-close",           4.00, 0.00, 0.0, 0.30),
    # s06
    ("cidade-a-noite",        0.00, 5.00, 1.0, None),
    ("palco-vazio",           0.00, 2.65, 1.0, None),
    ("palco-vazio",           2.65, 1.35, 0.5, None),   # slow 50% -> 2.70s
    ("palco-vazio",           4.00, 0.00, 0.0, 1.35),
    # s07
    ("moldura-vazia",         0.00, 5.00, 1.0, None),
    ("drone-oceano",          0.00, 5.00, 1.0, None),
    ("drone-oceano",          5.00, 0.00, 0.0, 0.44),
    # s08 — cartao sobre o freeze, fade para preto
    ("drone-oceano",          5.00, 0.00, 0.0, 6.66),
]


def duracao(caminho: str | pathlib.Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(caminho)],
        capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def saida_do_cue(src_dur: float, rate: float, out_dur: float | None) -> float:
    if rate == 0:
        if out_dur is None:
            raise ValueError("freeze exige out_dur")
        return out_dur
    return src_dur / rate


def build() -> dict:
    if not BROLL_MANIFEST.exists():
        raise SystemExit(f"{BROLL_MANIFEST} ausente — rode scripts.baixar_clipes_fal")
    manifesto = json.loads(BROLL_MANIFEST.read_text())

    # --- linha de tempo da voz: a espinha do filme ---
    vo, t = [], ABERTURA_SILENCIOSA
    for seg in SEGMENTOS:
        f = VO_DIR / f"{seg}.mp3"
        if not f.exists():
            raise SystemExit(f"{f} ausente — rode scripts.generate_vo_lote")
        d = duracao(f)
        vo.append({"seg": seg, "at": round(t, 3), "dur": round(d, 3), "src": str(f)})
        t += d
    fim_da_voz = t

    # --- trilha de imagem ---
    faltando = {s for s, *_ in SEQ} - set(manifesto)
    if faltando:
        raise SystemExit(f"clipes ausentes no manifesto: {sorted(faltando)}")

    video, at = [], 0.0
    for slug, entrada, src_dur, rate, out_dur in SEQ:
        caminho = manifesto[slug]["path"]
        disponivel = duracao(caminho)
        if entrada + src_dur > disponivel + 0.05:
            raise SystemExit(
                f"{slug}: cue pede {entrada + src_dur:.2f}s mas o clipe tem "
                f"{disponivel:.2f}s")
        dur = saida_do_cue(src_dur, rate, out_dur)
        video.append({
            "clip": slug, "src": caminho, "at": round(at, 3),
            "in": round(entrada, 3), "src_dur": round(src_dur, 3),
            "rate": rate, "dur": round(dur, 3),
            "fx": "freeze" if rate == 0 else ("slow" if rate < 1 else None),
        })
        at += dur
    fim_da_imagem = at

    # --- validacao: imagem e voz tem que fechar no mesmo ponto ---
    if abs(fim_da_imagem - fim_da_voz) > 0.05:
        raise SystemExit(
            f"decupagem nao fecha: imagem termina em {fim_da_imagem:.2f}s, "
            f"voz em {fim_da_voz:.2f}s (delta {fim_da_imagem - fim_da_voz:+.2f}s)")

    trilha_dur = duracao(TRILHA) if TRILHA.exists() else 0.0
    if trilha_dur and trilha_dur < fim_da_imagem - 0.05:
        raise SystemExit(
            f"trilha tem {trilha_dur:.2f}s e o filme tem {fim_da_imagem:.2f}s")

    s04 = next(v for v in vo if v["seg"] == "s04")
    s08 = next(v for v in vo if v["seg"] == "s08")

    return {
        "master": MASTER,
        "duration": round(fim_da_imagem, 3),
        "crossfade": CROSSFADE,
        "video": video,
        "vo": vo,
        # Nivel do leito em tres degraus, nao um valor unico: medindo o render,
        # -17 deixava a abertura sem voz em -40 dB (inaudivel no celular) e -12
        # ficava quente sob a narracao. A trilha abre alta, recua quando a voz
        # entra, e recua mais sob a unica fala de dialogo. Janelas NAO se
        # sobrepoem — o renderizador aplica os ganhos em sequencia.
        "bed": {
            "src": str(TRILHA),
            "gain_db": -10.0,
            "duck": [
                {"at": ABERTURA_SILENCIOSA, "dur": s04["at"] - ABERTURA_SILENCIOSA,
                 "gain_db": -17.0},                                    # s01..s03
                {"at": s04["at"], "dur": s04["dur"], "gain_db": -22.0},  # CETICA
                {"at": s04["at"] + s04["dur"],
                 "dur": fim_da_voz - (s04["at"] + s04["dur"]),
                 "gain_db": -17.0},                                    # s05..s08
            ],
            "fade_out": 2.0,
        },
        "disclosure": DISCLOSURE,
        "card": {"at": s08["at"], "dur": s08["dur"], "lines": CARTAO,
                 "fade_from_black": 1.2},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Gera o cue sheet do filme do motor.")
    ap.add_argument("--print", action="store_true", dest="imprimir",
                    help="imprime a linha de tempo em vez de so gravar")
    ap.add_argument("--out", default=str(SAIDA))
    args = ap.parse_args()

    cue = build()

    if args.imprimir:
        print(f"{'inicio':>8} {'fim':>8} {'dur':>6}  {'fx':<7} clipe")
        for v in cue["video"]:
            fim = v["at"] + v["dur"]
            print(f"{v['at']:>8.2f} {fim:>8.2f} {v['dur']:>6.2f}  "
                  f"{v['fx'] or '-':<7} {v['clip']}")
        print()
        for s in cue["vo"]:
            print(f"{s['at']:>8.2f} {s['at'] + s['dur']:>8.2f} {s['dur']:>6.2f}  "
                  f"{'voz':<7} {s['seg']}")
        print(f"\nfilme: {cue['duration']:.2f}s · {len(cue['video'])} cortes · "
              f"{len({v['clip'] for v in cue['video']})} clipes distintos")

    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.out).write_text(json.dumps(cue, indent=2, ensure_ascii=False))
    print(f"cue sheet: {args.out}")


if __name__ == "__main__":
    main()

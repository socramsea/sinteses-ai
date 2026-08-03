#!/usr/bin/env bash
# Montagem manual do piloto "terremoto da Venezuela" (job c5b824933ba095f5).
#
# Contexto: só 6 clipes de 8s (48s de imagem) foram gerados antes do job parar,
# mas a narração tem 4min12s. Este script estica os 6 clipes para cobrir os
# 252,3s da VO com slow-motion + ping-pong + ken burns, cortando sempre dentro
# das pausas da narração (limites extraídos com silencedetect).
#
# Uso: bash scripts/montar_venezuela.sh
set -euo pipefail

ROOT=/home/sea/Downloads/sintese
JOB=c5b824933ba095f5
WORK=$ROOT/.work/$JOB
TMP=$WORK/montagem
OUT=$ROOT/out/$JOB
VO=$WORK/vo.mp3
FONT=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
DISCLOSURE="Cenas recriadas por IA · imagens ilustrativas"
VO_DUR=252.312

mkdir -p "$TMP" "$OUT"

# ---------------------------------------------------------------- shot list
# Ordem = ordem de geração dos clipes (mtime), que segue a ordem das cenas.
# Duração de cada bloco = distância entre pausas da narração (silencedetect),
# escolhidas o mais perto possível de 1/6 da VO cada.
CLIPS=(
  ff97d504c1ce   # 1. mapa regional da Venezuela + epicentro (San Felipe)
  608a9358a87d   # 2. placas Caribe / Sul-Americana + falha de San Sebastián
  a2453355a912   # 3. corte geológico — Mw 7,2 (219 km) e Mw 7,5 (30 km)
  32df55acca27   # 4. sismograma 22:04:28 UTC — foreshock Mw 7,2
  38f35da77bcf   # 5. ruptura da rocha (fenda incandescente)
  4ebfdf8aa93f   # 6. ruptura da Falha 1 → transferência de estresse
)
DUR=(44.70 34.70 48.05 40.38 41.86 42.622)   # soma = 252.312 = duração da VO
XF=1.0                                        # crossfade entre blocos (s)

# ------------------------------------------------- etapa A: ping-pong 720p
# vai + volta no clipe original (8s -> 16s), ainda em 24fps/720p para o
# filtro reverse não estourar memória.
for c in "${CLIPS[@]}"; do
  [ -f "$TMP/pp_$c.mp4" ] && continue
  echo ">> ping-pong $c"
  ffmpeg -v warning -y -i "$WORK/clips/$c.mp4" \
    -filter_complex "[0:v]scale=1280:720,setsar=1,split=2[a][b];[b]reverse[r];[a][r]concat=n=2:v=1[v]" \
    -map "[v]" -an -c:v libx264 -crf 16 -preset veryfast -pix_fmt yuv420p "$TMP/pp_$c.mp4"
done

# ------------------------------------- etapa B: esticar cada bloco na VO
# ping-pong em loop + slow 50% + interpolação + ken burns (zoom lento 6%),
# alternando zoom-in / zoom-out para o olho não perceber a repetição.
for i in "${!CLIPS[@]}"; do
  c=${CLIPS[$i]}
  d=${DUR[$i]}
  L=$(python3 -c "print(f'{${d} + ${XF}:.3f}')")   # +crossfade de saída
  [ -f "$TMP/seg_$i.mp4" ] && continue

  if [ $((i % 2)) -eq 0 ]; then
    Z="(1+0.06*t/$L)"                              # zoom in  (1.00 -> 1.06)
  else
    Z="(1.06-0.06*t/$L)"                           # zoom out (1.06 -> 1.00)
  fi
  case $i in
    1|4) X="(in_w-out_w)*(0.15+0.70*t/$L)" ;;      # pan lateral suave
    *)   X="(in_w-out_w)/2" ;;                     # centralizado
  esac

  echo ">> bloco $i ($c) — ${L}s"
  ffmpeg -v warning -y -stream_loop -1 -i "$TMP/pp_$c.mp4" -t "$L" \
    -vf "setpts=2.0*PTS,minterpolate=fps=30:mi_mode=blend,\
scale=1920:1080:flags=lanczos,\
scale=w='ceil(1920*$Z/2)*2':h='ceil(1080*$Z/2)*2':eval=frame:flags=bicubic,\
crop=1920:1080:x='$X':y='(in_h-out_h)/2',setsar=1" \
    -an -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p "$TMP/seg_$i.mp4"
done

# ----------------------------------------- etapa C: crossfades + master
# offset de cada xfade = soma das durações dos blocos anteriores, então
# cada corte cai exatamente na pausa da narração.
INPUTS=(); for i in "${!CLIPS[@]}"; do INPUTS+=(-i "$TMP/seg_$i.mp4"); done
FC=""; PREV="0:v"; ACC=0
for i in $(seq 1 $(( ${#CLIPS[@]} - 1 ))); do
  ACC=$(python3 -c "print(f'{$ACC + ${DUR[$((i-1))]}:.3f}')")
  FC+="[$PREV][$i:v]xfade=transition=fade:duration=$XF:offset=$ACC[x$i];"
  PREV="x$i"
done
# disclosure de IA queimado, persistente (compliance) + fade de abertura/fecho
FC+="[$PREV]drawtext=fontfile=$FONT:text='$DISCLOSURE':fontsize=26:\
fontcolor=white@0.92:box=1:boxcolor=black@0.45:boxborderw=14:\
x=(w-text_w)/2:y=h-72,fade=t=in:st=0:d=1.2,fade=t=out:st=$(python3 -c "print(f'{$VO_DUR-2:.3f}')"):d=2[vout]"

echo ">> master 16:9"
ffmpeg -v warning -y "${INPUTS[@]}" -i "$VO" \
  -filter_complex "$FC" \
  -map "[vout]" -map "${#CLIPS[@]}:a" \
  -af "loudnorm=I=-16:TP=-1.5:LRA=11" \
  -t "$VO_DUR" -r 30 \
  -c:v libx264 -crf 19 -preset medium -pix_fmt yuv420p \
  -c:a aac -b:a 192k -movflags +faststart \
  "$WORK/master.mp4"

cp "$WORK/master.mp4" "$OUT/video_16x9.mp4"

# --------------------------------------------------- etapa D: 9:16 vertical
# Crop central cortaria os rótulos dos mapas/diagramas, então o 16:9 entra
# inteiro com fundo desfocado (padrão Shorts/Reels para conteúdo gráfico).
echo ">> export 9:16"
ffmpeg -v warning -y -i "$WORK/master.mp4" \
  -filter_complex "[0:v]split=2[bg][fg];\
[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,\
boxblur=luma_radius=40:luma_power=2,eq=brightness=-0.12[bgb];\
[fg]scale=1080:-2[fgs];\
[bgb][fgs]overlay=(W-w)/2:(H-h)/2,setsar=1[v]" \
  -map "[v]" -map 0:a -c:v libx264 -crf 20 -preset medium -pix_fmt yuv420p \
  -c:a copy -movflags +faststart "$OUT/video_9x16.mp4"

echo
echo "OK:"
ls -lh "$WORK/master.mp4" "$OUT/video_16x9.mp4" "$OUT/video_9x16.mp4"

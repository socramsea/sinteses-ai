# Mapa de Montagem — Filme do Motor (93,4s · 9:16 nativo)

Peça de portfólio: apresenta o Síntese narrando sobre imagem de geração própria.

**Master 9:16 (1080x1920), 24fps.** O material-fonte é vertical — os 16 clipes
saíram em 1080x1920. Não há master 16:9: de uma fonte com 1080 de largura não se
tira 1920 sem escalar 1,78x e cortar altura, e nos planos fechados (olhos, mãos)
isso inviabiliza o enquadramento. Vertical íntegro vale mais que horizontal
remendado.

> ⚠️ Não usar `export.py` para gerar 16:9 a partir deste master: a linha 26 faz
> `resized((1920,1080))` sem preservar proporção e **achata** a imagem. O caminho
> 16:9 assume master já horizontal.

## Material

**Imagem** — `.work/motor-broll/`, 16 clipes, 78s no total, todos 1080x1920.
Baixados por `scripts/baixar_clipes_fal.py`; `manifest.json` liga slug → arquivo.

**Voz** — `out/motor-vo/s01..s08.mp3`, 81,43s. Roteiro: `prompts/vo_motor.txt`.
NARRADORA `Voice6d64b7cc1784772153`, CETICA `Voice43759aae1784770778`.

**Trilha** — `out/trilhas/trilha-motor.wav`, 94,0s, gerada sob medida no
`stable-audio-25`. Os leitos antigos (`trilha-a`, `trilha-b`) têm 61s e não
servem: loop de trilha em documentário se ouve na emenda.

## Decupagem

| Tempo | Voz | Imagem |
|---|---|---|
| 0:00–0:06 | — | `black-ponto-de-luz` — abre no preto, trilha entrando mínima |
| 0:06–0:10 | — | `feixe-de-projetor` — a luz se acende |
| 0:10–0:12 | — | `particulas-de-luz` (2s iniciais) |
| 12,00–14,00 | **s01** | `particulas-de-luz` (2s finais) |
| 14,00–17,65 | s01 | `estroboscopio-dourado` |
| 17,65–22,65 | **s02** | `tela-apagando` |
| 22,65–30,65 | s02 | `silhueta-monitores` — entra em "o motor que percorre esse caminho" |
| 30,65–31,66 | s02 | **FREEZE** + zoom 3%, segura em "Síntese" |
| 31,66–35,66 | **s03** | `maos-calejadas` |
| 35,66–39,66 | s03 | `sala-de-reuniao-vazia` |
| 39,66–46,49 | s03 | `escritorio-vazio` |
| 46,49–49,33 | **s04** (CETICA) | **FREEZE** no último frame + zoom 3%; trilha recua |
| 49,33–50,33 | **s05** | descongela em **slow 50%** |
| 50,33–55,33 | s05 | `multidao-desfocada` |
| 55,33–59,33 | s05 | `multidao-foco-revela` — o foco achando a figura = retomar |
| 59,33–63,33 | s05 | `olhos-close` |
| 63,33–64,63 | s05 | `olhos-close` em **slow 50%** |
| 64,63–69,63 | **s06** | `cidade-a-noite` |
| 69,63–73,63 | s06 | `palco-vazio` |
| 73,63–76,33 | s06 | `palco-vazio` em **slow 50%** |
| 76,33–81,33 | **s07** | `moldura-vazia` — moldura sem foto = afirmação sem fonte |
| 81,33–86,33 | s07 | `drone-oceano` |
| 86,33–86,77 | s07 | **FREEZE** |
| 86,77–93,43 | **s08** | fade para preto + cartão `github.com/socramsea/sinteses-ai` |

Os 16 clipes são usados, nenhum repetido. 78s de imagem + 9,3s de freeze/slow +
6,2s de cartão = 93,4s. A trilha de 94,0s cobre com 0,6s de cauda.

## Regras

- Crossfade 3–4s dentro dos blocos; nunca corte seco na abertura silenciosa
- Freeze sempre no ápice do movimento + zoom lento 3–5%
- Descongelar em slow 50% por 1s
- Trilha recua sob a fala da CETICA (s04) e volta no descongelamento
- Nada no médio da trilha que dispute com a narração

## Pendências

- [ ] Montar
- [ ] Legenda queimada em pt-BR (9:16 é assistido sem som na maior parte)
- [ ] Disclosure de IA no rodapé — o próprio filme exige isso na s07

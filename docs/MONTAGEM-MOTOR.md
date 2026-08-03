# Mapa de Montagem — Filme do Motor (~90s)

Peça de portfólio: apresenta o Síntese narrando sobre o próprio output. Todo clipe
usado aqui **foi gerado por este pipeline** — o nome de arquivo é `md5(url)[:12].mp4`,
o padrão de cache do `video_provider.py:85`. A imagem é a evidência, não ilustração.

Master 16:9 · 24fps · 9:16 derivado depois do master aprovado.
VO: `prompts/vo_motor.txt` (pt-BR) e `prompts/vo_motor.en.txt` (inglês).

## Material — tudo já em disco, nada a gerar

| Clipe | Origem | Conteúdo |
|---|---|---|
| `adc01eda1ab0` | `.work/brandfilm-ato1/` | aérea da costa |
| `d8ee9bf5722f` | `.work/brandfilm-ato1/` | onda na pedra |
| `8f93e747fd03` | `.work/brandfilm-ato1/` | macro água |
| `61da9d4148b1` | `.work/brandfilm-ato1/` | a espera |
| `08192357ff83` | `.work/brandfilm-ato1/` | aparição da jubarte |
| `0836151bd147` | `.work/brandfilm-ato1/` | nadadeira |
| 6 clipes da travessia | `work-backup/c5b824933ba095f5/clips/` | escolher 2 para 1:01–1:24 |

Todos 8s, 1280x720. Trilha: `out/trilhas/trilha-a-piano-cordas.wav` (61s).

## Decupagem

Tempos de VO são **estimativa** (~11,5 char/s + pausas). Fechar depois de gerar —
regra herdada: o ritmo do corte segue a voz, nunca o contrário.

| Tempo | Voz | Imagem |
|---|---|---|
| 0:00–0:08 | — | `adc01eda1ab0`, trilha entrando mínima |
| 0:08–0:12 | — | `d8ee9bf5722f` |
| 0:12–0:17 | s01 | `d8ee9bf5722f` seguindo; **CONGELA** no impacto, em "filmado" |
| 0:17–0:29 | s02 | descongela em slow 50%, corta para `8f93e747fd03` |
| 0:29–0:43 | s03 | `61da9d4148b1`; vira para `08192357ff83` em "gera as reconstituições" |
| 0:43–0:47 | s04 (CETICA) | **FREEZE** em `08192357ff83` + silêncio na trilha |
| 0:47–1:01 | s05 | `0836151bd147` em slow 50% |
| 1:01–1:13 | s06 | travessia — clipe 1 dos 6 |
| 1:13–1:24 | s07 | travessia — clipe 2 |
| 1:24–1:30 | s08 | tela limpa: mar + cartão `github.com/socramsea/sinteses-ai` |

## Regras (herdadas do MONTAGEM.md)

- Crossfade 3–4s; nunca corte seco na abertura silenciosa
- Freeze sempre no ápice do movimento + zoom lento 3–5%
- Descongelar em slow 50% por 1s
- 9:16 só depois do master 16:9 aprovado

## Pendências

- [ ] Gerar o VO (~825 caracteres pt-BR ≈ US$0,08; inglês ≈ US$0,09 no MiniMax)
- [ ] Escolher 2 dos 6 clipes da travessia para s06/s07
- [ ] **Trilha cobre 61s, o filme tem ~90s** — estender o leito, encadear as duas
      trilhas, ou cortar o roteiro. Decidir depois de ouvir o VO real
- [ ] Voz inglesa: os ids MiniMax são pt-BR. Ou escolher voz inglesa no painel da
      fal, ou usar o `edge-tts` do motor (`lang="en"`, gratuito)

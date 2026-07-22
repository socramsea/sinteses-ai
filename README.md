# Síntese — Documentary Synthesis Engine (WSS+13)

Motor que transforma **eventos reais** em **documentários curtos** ("síntese do que
aconteceu") para canal dark no YouTube / Shorts / Reels / TikTok. Pesquisa com fonte,
gera reconstituições por IA + camada geográfica, narra, monta e exporta multi-formato.

Reaproveita o motor de vídeo do NutriDeby (FFmpeg/MoviePy/edge-tts/Redis/FastAPI).
Stack: **Python 3.12 · FastAPI · Redis · FFmpeg · Docker · DigitalOcean**. Sem Node no backend.

## Subir

```bash
cp .env.example .env      # preencha as credenciais (server-side)
make up                   # api + worker + redis via docker compose
make enqueue              # enfileira o piloto: terremoto Venezuela 24/06/2026
Status

POST /jobs → 202 + job_id (assíncrono, idempotente)

GET /jobs/{id} → estágio, custo, artefatos (polling)

GET /health

Compliance

Disclosure de IA, fonte obrigatória e bloqueio de "IA-como-filmagem-real" são
aplicados no código. Ver docs/COMPLIANCE.md. Conteúdo sensível passa por revisão
humana antes de publicar.

Estrutura
app/
  main.py            FastAPI + rotas
  config.py          settings (creds server-side)
  api/               schemas + rotas de job (202/polling)
  core/              state machine (Redis), budget, errors
  pipeline/          research → scenes → compliance → video → narration → assembly → export → geo
  workers/           worker (consome fila, roda orquestrador)
  storage/           upload Spaces
prompts/             research_system.md (cacheado), scene_director.md
scripts/             enqueue_example.py (piloto Venezuela)
tests/               state + compliance
docs/                ARCHITECTURE.md, COMPLIANCE.md

Roadmap curto

[ ] frames Earth Studio do piloto em assets/geo/<slug>/

[ ] calibrar custo real do fal em core/budget.py

[ ] trilha licenciada + color grade em assembly.py

[ ] publicação automática (YouTube Data API) no estágio PUBLISHING

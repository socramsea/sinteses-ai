# Síntese — Arquitetura

Motor de **documentários sintéticos** (canal dark) da WSS+13. Recebe um evento real,
pesquisa/roteiriza com fonte, gera cenas de reconstituição por IA + camada
geográfica, narra, monta e exporta multi-formato. Reaproveita ~80% do motor de
vídeo do NutriDeby (FFmpeg/MoviePy/edge-tts/Redis/FastAPI).

## Fluxo (assíncrono, polling — sem webhook)


POST /jobs ──202+job_id──▶ Redis queue ──▶ worker ──▶ orchestrator
│
┌──────────────────────────────────────┴───────────────────────────────┐
RESEARCH → SCRIPTING →[compliance gate]→ GENERATING → NARRATING → ASSEMBLING → EXPORTING → DONE
(anthropic)  (scenes)   (block/flags)     (fal.ai)     (edge-tts)   (moviepy)   (16:9/9:16)

GET /jobs/{id} ◀── polling de status

text

## Decisões herdadas do RFC-001 (render-to-video)
- **Polling, não webhook** — nenhum endpoint público novo enquanto o host não for
  reconstruído. (ADR-01)
- **Credencial 100% server-side**, nunca em log (`config.safe_dump`).
- **Custo é requisito** — teto por job, corte de cenas, idempotência. (ADR-03)
- **Slug de modelo nunca chumbado** — `FAL_MODEL_I2V/T2V` em config.
- **Sem Node no backend** — Python/FastAPI.

## Componentes novos (vs. render-to-video)
- `pipeline/research.py` — fatos→roteiro com fontes (Anthropic, prompt cacheado).
- `pipeline/geo.py` — camada geográfica (assets Earth Studio) = diferencial.
- `pipeline/compliance.py` — gate de disclosure/fonte/evento-sensível.
- `pipeline/export.py` — 1 master → vários formatos (YouTube + Shorts/Reels/TikTok).

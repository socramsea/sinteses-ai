# Síntese — Documentary Synthesis Engine

![Python](https://img.shields.io/badge/Python-3.12-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-async-009688) ![Redis](https://img.shields.io/badge/Redis-queue-DC382D) ![Docker](https://img.shields.io/badge/Docker-compose-2496ED)

A production pipeline that turns real-world events into short documentary films.

Given a sourced event, the engine researches it, breaks it into scenes, generates AI reconstructions through video generation APIs, adds a geographic layer, narrates, assembles, and exports to multiple aspect ratios — as an asynchronous, resumable job.

Built and operated by a single engineer. Deployed on DigitalOcean and producing finished multi-scene films, not prototypes.

**Stack:** Python 3.12 · FastAPI · Redis · FFmpeg · MoviePy · Docker · DigitalOcean

Portuguese version: [README.pt-BR.md](README.pt-BR.md).

## What it does

A job is submitted once and moves through stages independently of the client connection:

    research → scenes → compliance → video → narration → assembly → export → geo

Each stage is a discrete module under `app/pipeline/`. State transitions are persisted in Redis, so a job survives worker restarts and reports its current stage, accumulated cost, and produced artifacts at any point.

Design decisions worth noting:

- **Asynchronous by default.** Generation calls take minutes. `POST /jobs` returns `202` immediately with a job ID; progress is retrieved by polling.
- **Idempotent submission.** The job ID is a hash of the request payload, so replaying the same request returns the existing job instead of enqueueing duplicate work.
- **Cost ceiling enforced in code.** `app/core/budget.py` projects the cost of the next stage and aborts *before* calling a paid provider if it would exceed `JOB_BUDGET_BRL_MAX`; scene count is capped separately to stop runaway jobs. Per-unit figures are estimates until calibrated against provider invoices.
- **Compliance enforced in code**, not in policy documents. See below.
- **Credentials stay server-side.** No generation keys reach the client.

## Architecture

    app/
      main.py            FastAPI application and routes
      config.py          settings, server-side credentials
      api/               request/response schemas, job routes (202 + polling)
      core/              Redis-backed state machine, budget tracking, error types
      pipeline/          the eight pipeline stages
      workers/           queue consumer running the orchestrator
      storage/           object storage upload (DigitalOcean Spaces)
    prompts/             research_system.md (cached), scene_director.md, vo_brandfilm.txt
    scripts/             enqueue_example.py (reference job) + production utilities
    tests/               state machine, job-id derivation, compliance
    docs/                ARCHITECTURE.md, COMPLIANCE.md

API and worker run as separate containers sharing a Redis instance. Scaling render throughput means adding workers, not touching the API.

## API

| Method | Route | Behaviour |
| --- | --- | --- |
| `POST` | `/jobs` | Enqueue a job. Returns `202` with a job ID. Idempotent. |
| `GET` | `/jobs/{id}` | Current stage, accumulated cost, produced artifacts. |
| `GET` | `/health` | Liveness check. |

## Running it

This is a live system, not a self-contained demo. A full run needs paid credentials for a video generation provider and object storage — see `.env.example` for the full list. Docker and Docker Compose are required.

    cp .env.example .env      # fill in credentials (server-side only)
    make up                   # api + worker + redis via docker compose
    make enqueue              # enqueue the reference job

Without generation credentials the API, worker, state machine and compliance stage still run.

## Tests

The suite needs no credentials and no Redis — the state machine is exercised against an in-memory double, so a clean clone can verify it:

    pip install -r requirements-dev.txt
    make test                 # 14 tests, ~1s

Covering the state machine (persistence, queue idempotency, tolerance of older job schemas), job-id derivation, and the compliance blocks.

## Compliance

Generative documentary content carries a specific risk: audiences mistaking synthetic reconstruction for real footage. Three rules are enforced in the pipeline itself, not left to editorial discretion:

- **AI disclosure** is attached to output.
- **Sourcing is mandatory** — a job without a verifiable source for the underlying event does not proceed past the research stage.
- **AI-as-real-footage is blocked** at the compliance stage.

Sensitive subject matter is routed to human review before publication. Details in `docs/COMPLIANCE.md`.

## Roadmap

- [ ] Geographic frames for the reference job under `assets/geo/<slug>/` (media data, kept out of the repo)
- [ ] Calibrate real per-unit generation cost in `core/budget.py` against provider invoices
- [ ] Licensed score and colour grade in `assembly.py`
- [ ] Automated publishing at the `PUBLISHING` stage

## License

See `LICENSE`.

## Author

Marcos Sea — AI and automation engineer, Forja Criativa.
[forjacriativa.ia.br](https://forjacriativa.ia.br/) · [github.com/socramsea](https://github.com/socramsea)

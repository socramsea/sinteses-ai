# Síntese — Documentary Synthesis Engine

![Python](https://img.shields.io/badge/Python-3.12-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-async-009688) ![Redis](https://img.shields.io/badge/Redis-queue-DC382D) ![Docker](https://img.shields.io/badge/Docker-compose-2496ED)

> Versão em português. English: [README.md](README.md).

Motor que transforma **eventos reais** em **documentários curtos** — a síntese do que
aconteceu. Pesquisa com fonte, quebra em cenas, gera reconstituições por IA, adiciona
camada geográfica, narra, monta e exporta multi-formato. Tudo como job assíncrono e
retomável.

Construído e operado por um engenheiro só. Roda em DigitalOcean.

**Stack:** Python 3.12 · FastAPI · Redis · FFmpeg · MoviePy · Docker · DigitalOcean. Sem Node no backend.

## O que faz

O job é submetido uma vez e avança independente da conexão do cliente:

    research → scenes → compliance → video → narration → assembly → export → geo

Cada estágio é um módulo em `app/pipeline/`. As transições são persistidas em Redis,
então o job sobrevive a restart de worker e reporta estágio, custo acumulado e
artefatos produzidos a qualquer momento.

Decisões de projeto que valem nota:

- **Assíncrono por padrão.** Geração leva minutos. `POST /jobs` devolve `202` na hora com um id; progresso por polling.
- **Submissão idempotente.** O id do job é hash do payload — reenviar o mesmo pedido devolve o job existente em vez de enfileirar trabalho duplicado.
- **Teto de custo aplicado no código.** `app/core/budget.py` projeta o custo do próximo estágio e aborta antes de chamar provider pago se estourar o teto.
- **Compliance no código**, não em documento de política. Ver abaixo.
- **Credencial não sai do servidor.** Nenhuma chave de geração chega ao cliente.
- **Bilíngue por construção.** O `lang` decide o idioma do roteiro *e* a voz da narração, e entra no hash do job_id — o mesmo evento vira dois jobs independentes, cada um retomável por conta própria, em vez de um job com duas saídas.

## Arquitetura

    app/
      main.py            FastAPI e rotas
      config.py          settings, credenciais server-side
      api/               schemas de request/response, rotas de job (202 + polling)
      core/              state machine em Redis, controle de custo, tipos de erro
      pipeline/          os oito estágios
      workers/           consumidor da fila rodando o orquestrador
      storage/           upload para object storage (DigitalOcean Spaces)
    prompts/             research_system.md (cacheado), scene_director.md, vo_brandfilm.txt
    scripts/             enqueue_example.py (job de referência) + utilitários de produção
    tests/               state machine, idempotência e compliance
    docs/                ARCHITECTURE.md, COMPLIANCE.md

API e worker rodam em containers separados compartilhando um Redis. Escalar
throughput de render é adicionar worker, não mexer na API.

## API

| Método | Rota | Comportamento |
| --- | --- | --- |
| `POST` | `/jobs` | Enfileira um job. Devolve `202` com o id. Idempotente. |
| `GET` | `/jobs/{id}` | Estágio atual, custo acumulado, artefatos produzidos. |
| `GET` | `/health` | Liveness. |

## Subir

Um run completo precisa de credencial paga de provider de vídeo e de object
storage — a lista completa está em `.env.example`. Requer Docker e Docker Compose.

```bash
cp .env.example .env      # preencha as credenciais (server-side)
make up                   # api + worker + redis via docker compose
make enqueue              # job de referência, narração em português
make enqueue-en           # mesmo evento, narração em inglês
```

## Testes

Sem credencial, sem Redis, sem gerar um frame: o Redis é um duplo em memória e todo
estágio pago é falseado, então um clone limpo verifica a lógica do motor.

```bash
pip install -r requirements-dev.txt
make test                 # 47 testes, ~1s
```

Plano de cenas, compliance e budget rodam de verdade; só o provider de vídeo, o TTS,
a montagem e o export são falseados. É isso que torna a retomada verificável em vez
de retórica — a suite prova que um job reiniciado com 1 de 3 clipes prontos chama o
provider exatamente duas vezes, e que uma falha de compliance ou de orçamento aborta
antes de qualquer chamada paga.

Cobre o orquestrador (os dois modos, retomada, guard-rails, roteamento de idioma,
asset geográfico), a máquina de estados, a derivação do id do job, a resolução de voz
e os bloqueios de compliance.

## Compliance

Documentário generativo carrega um risco específico: a audiência confundir
reconstituição sintética com filmagem real. Três regras são aplicadas no próprio
pipeline, não deixadas a critério editorial:

- **Disclosure de IA** é anexado à saída.
- **Fonte é obrigatória** — job sem fonte verificável do evento não passa da pesquisa.
- **IA-como-filmagem-real** é bloqueada no estágio de compliance.

Conteúdo sensível é roteado para revisão humana antes de publicar. Detalhes em
`docs/COMPLIANCE.md`.

## Roadmap

- [ ] Frames geográficos do job de referência em `assets/geo/<slug>/` (dado de mídia, fora do repo)
- [ ] Calibrar custo real por unidade em `core/budget.py` com a fatura do provider
- [ ] Trilha licenciada e color grade em `assembly.py`
- [ ] Publicação automática (YouTube Data API) no estágio `PUBLISHING`

## Licença

Ver `LICENSE`.

## Autor

Marcos Sea — engenheiro de IA e automação, Forja Criativa.
[forjacriativa.ia.br](https://forjacriativa.ia.br/) · [github.com/socramsea](https://github.com/socramsea)

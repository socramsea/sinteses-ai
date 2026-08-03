.PHONY: up down logs api worker test fmt enqueue enqueue-en enqueue-both

up:        ## sobe stack (api + worker + redis)
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=120

api:       ## roda a api local (sem docker)
	uvicorn app.main:app --reload --port 8080

worker:    ## roda o worker local (sem docker)
	python -m app.workers.worker

test:
	pytest -q

# -m e não caminho de arquivo: sem PYTHONPATH, `python scripts/x.py` não enxerga app/
enqueue:   ## enfileira o piloto (terremoto Venezuela) em pt-BR
	python -m scripts.enqueue_example

enqueue-en: ## enfileira o piloto em inglês
	python -m scripts.enqueue_example --lang en

enqueue-both: ## enfileira o piloto nos dois idiomas
	python -m scripts.enqueue_example --both

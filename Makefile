.PHONY: up down logs api worker test fmt enqueue

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

enqueue:   ## enfileira o piloto (terremoto Venezuela)
	python scripts/enqueue_example.py

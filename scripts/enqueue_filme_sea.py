"""Filme SEA: jornada da jubarte em 4 cenas (modo criativo).
Fundo da pagina sea-filme + anuncio 9:16. Sem narracao (mudo).
Uso: python -m scripts.enqueue_filme_sea
"""
from app.core.state import Job, enqueue
from app.api.schemas import JobRequest, Scene

ESTILO = ("golden hour light, crystal-clear turquoise ocean, National Geographic "
          "documentary style, stabilized aerial drone footage, slow graceful "
          "motion, single continuous shot, no cuts, no text")

req = JobRequest(
    topic="SEA — jornada da jubarte (fundo cinematografico)",
    lang="pt-BR",
    formats=["16:9", "9:16"],
    mode="creative",
    scenes=[
        Scene(visual_prompt=f"Drone flying low over open ocean toward the setting sun, gentle waves, golden path on the water, no land, {ESTILO}", duration_s=8.0),
        Scene(visual_prompt=f"Humpback whale slapping its long white pectoral fin on the ocean surface, big splash of water, aerial view, {ESTILO}", duration_s=8.0),
        Scene(visual_prompt=f"Aerial shot following a humpback whale traveling steadily just beneath the surface, wake trail behind it, sense of journey, {ESTILO}", duration_s=8.0),
        Scene(visual_prompt=f"Aerial top-down shot, humpback whale mother gliding beneath the surface with her calf close to her side, white pectoral fins visible, sunlight caustics, {ESTILO}", duration_s=8.0),
    ],
    disclosure=True,
)
scene_dicts = [s.model_dump() for s in req.scenes]
job = Job(job_id=req.idempotency_id(), topic=req.topic, lang=req.lang,
          formats=req.formats, mode=req.mode, scenes=scene_dicts,
          disclosure=req.disclosure)
enqueue(job)
print(f"enfileirado filme job_id={job.job_id} (formatos {req.formats})")

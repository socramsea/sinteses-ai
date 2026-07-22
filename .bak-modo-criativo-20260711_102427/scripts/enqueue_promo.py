"""Enfileira o promo da NutriDeby — "Um dia com a Deby" (modo criativo).
Uso: python scripts/enqueue_promo.py

Modo criativo: sem pesquisa/fonte factual, encenação permitida, disclosure de IA mantido.
A tela do WhatsApp da Deby entra como OVERLAY na montagem (assembly.py), usando o
mockup pronto — o gerador de vídeo cuida só da cena real (cozinha, mão, luz, rosto).
"""
from app.core.state import Job, enqueue
from app.api.schemas import JobRequest, Scene

SCENES = [
    Scene(
        visual_prompt=(
            "Cozinha doméstica brasileira, manhã, luz natural quente entrando pela janela. "
            "Câmera lenta, plano médio, lente 35mm, profundidade rasa. Tigela de frutas frescas "
            "e ervas sobre bancada de madeira clara. Partículas de poeira flutuando na luz dourada. "
            "Paleta verde e creme, aconchegante."
        ),
        duration_s=2.5,
    ),
    Scene(
        visual_prompt=(
            "Close da mão de uma pessoa pegando um smartphone da bancada. Câmera lenta, macro 50mm, "
            "foco na mão e no aparelho, fundo desfocado da cozinha iluminada. Movimento suave de subida."
        ),
        duration_s=2.0,
    ),
    Scene(
        visual_prompt=(
            "Vista de cima (top-down) de um prato colorido e saudável — arroz, feijão, frango grelhado, "
            "salada e tomate — sobre mesa de madeira. A tela do celular entra em quadro enquanto a pessoa "
            "fotografa o prato. Luz natural difusa, cores vivas e apetitosas, câmera lenta."
        ),
        duration_s=2.5,
        overlay="whatsapp_deby_recebe_foto",   # mockup da conversa recebendo a foto
    ),
    Scene(
        visual_prompt=(
            "Close da tela do smartphone nas mãos da pessoa, foco raso, rosto desfocado sorrindo ao fundo. "
            "Luz quente refletindo na tela. Movimento de câmera mínimo, contemplativo."
        ),
        duration_s=2.5,
        overlay="whatsapp_deby_resposta_taco",  # bolha da Deby + selo Fonte: TACO
    ),
    Scene(
        visual_prompt=(
            "Retrato em plano fechado de uma pessoa sorrindo levemente, satisfeita, olhando o celular. "
            "Luz dourada lateral, fundo de cozinha desfocado. Câmera lenta, lente 85mm, pele natural, "
            "expressão genuína e calma."
        ),
        duration_s=2.0,
    ),
    Scene(
        visual_prompt=(
            "Fundo verde-floresta limpo, transição suave a partir do brilho anterior. Espaço negativo "
            "generoso ao centro. Luz suave. Movimento de câmera imperceptível (respiração)."
        ),
        duration_s=2.5,
        overlay="logo_nutrideby_cta",           # logo + Deby acenando + 'Comece no WhatsApp'
        narration=None,
    ),
]

req = JobRequest(
    topic="NutriDeby — promo 'Um dia com a Deby'",
    mode="creative",
    lang="pt-BR",
    formats=["9:16", "16:9"],   # 9:16 Reels/TikTok/Shorts, 16:9 fundo do hero
    scenes=SCENES,
    disclosure=True,
)

# narração opcional para a versão de anúncio (comente para hero mudo)
req.scenes[2].narration = "Você fotografa o prato."
req.scenes[3].narration = "A Deby entende na hora, com fonte oficial."
req.scenes[4].narration = "E uma nutricionista de verdade acompanha."
req.scenes[5].narration = "NutriDeby — sua saúde, todos os dias, no seu WhatsApp."

# scenes -> dicts para persistir no Job (Pydantic v2: model_dump; v1: use .dict())
scene_dicts = [s.model_dump() for s in req.scenes]

job = Job(
    job_id=req.idempotency_id(),
    topic=req.topic,
    lang=req.lang,
    formats=req.formats,
    mode=req.mode,
    scenes=scene_dicts,
    disclosure=req.disclosure,
)
enqueue(job)
print(f"enfileirado promo job_id={job.job_id} (formatos {req.formats})")

"""Enfileira o promo da NutriDeby — "Um dia com a Deby" (modo criativo).
Uso: python scripts/enqueue_promo.py  (ou de dentro de container)

REGRA DE FERRO CONTRA ERRO DE PORTUGUÊS:
- A IA (Veo3/Kling) é PROIBIDA de escrever qualquer texto na cena (ela erra ortografia).
  Por isso todo visual_prompt termina com NO_TEXT (instrução negativa).
- TODO texto do vídeo é OVERLAY nosso, digitado em pt-BR correto e sobreposto na montagem:
  a tela do WhatsApp da Deby, legendas, logo e o CTA "Comece no WhatsApp".
- A narração (quando ativa) usa voz neural pt-BR; o roteiro é escrito por nós.
"""
from app.core.state import Job, enqueue
from app.api.schemas import JobRequest, Scene

# instrução negativa anexada a TODA cena: a IA não desenha texto nenhum
NO_TEXT = (" Sem qualquer texto, letras, palavras, placas, legendas, números "
           "ou marcas escritas visíveis na cena. Nenhuma tela com texto legível.")

SCENES = [
    Scene(
        visual_prompt=(
            "Cozinha doméstica brasileira, manhã, luz natural quente entrando pela janela. "
            "Câmera lenta, plano médio, lente 35mm, profundidade rasa. Tigela de frutas frescas "
            "e ervas sobre bancada de madeira clara. Partículas de poeira flutuando na luz dourada. "
            "Paleta verde e creme, aconchegante." + NO_TEXT
        ),
        duration_s=2.5,
    ),
    Scene(
        visual_prompt=(
            "Close da mão de uma pessoa pegando um smartphone da bancada. Câmera lenta, macro 50mm, "
            "foco na mão e no aparelho, fundo desfocado da cozinha iluminada. A tela do celular "
            "aparece apagada ou com brilho neutro, sem interface. Movimento suave de subida." + NO_TEXT
        ),
        duration_s=2.0,
    ),
    Scene(
        visual_prompt=(
            "Vista de cima (top-down) de um prato colorido e saudável — arroz, feijão, frango grelhado, "
            "salada e tomate — sobre mesa de madeira. Uma mão segura o celular fotografando o prato. "
            "Luz natural difusa, cores vivas e apetitosas, câmera lenta." + NO_TEXT
        ),
        duration_s=2.5,
        overlay="whatsapp_deby_recebe_foto",   # mockup da conversa (texto pt-BR nosso) por cima
    ),
    Scene(
        visual_prompt=(
            "Close da tela de um smartphone nas mãos de uma pessoa, foco raso, rosto desfocado sorrindo "
            "ao fundo. Luz quente refletindo na tela, que aparece com brilho neutro, sem interface. "
            "Movimento de câmera mínimo, contemplativo." + NO_TEXT
        ),
        duration_s=2.5,
        overlay="whatsapp_deby_resposta_taco",  # bolha da Deby + selo (texto pt-BR nosso)
    ),
    Scene(
        visual_prompt=(
            "Retrato em plano fechado de uma pessoa sorrindo levemente, satisfeita, olhando o celular. "
            "Luz dourada lateral, fundo de cozinha desfocado. Câmera lenta, lente 85mm, pele natural, "
            "expressão genuína e calma." + NO_TEXT
        ),
        duration_s=2.0,
    ),
    Scene(
        visual_prompt=(
            "Fundo verde-floresta limpo e liso, transição suave a partir do brilho anterior. Espaço "
            "negativo generoso ao centro. Luz suave. Movimento de câmera imperceptível (respiração)." + NO_TEXT
        ),
        duration_s=2.5,
        overlay="logo_nutrideby_cta",           # logo + Deby + 'Comece no WhatsApp' (texto pt-BR nosso)
    ),
]

req = JobRequest(
    topic="NutriDeby — promo 'Um dia com a Deby'",
    mode="creative",
    lang="pt-BR",
    formats=["9:16", "16:9"],
    scenes=SCENES,
    disclosure=True,
)

# Narração opcional (voz pt-BR). Comente estas linhas para HERO MUDO.
# Recomendo trocar a voz padrão para pt-BR-FranciscaNeural (feminina, acolhedora) em narration.py.
req.scenes[2].narration = "Você fotografa o prato."
req.scenes[3].narration = "A Deby entende na hora, com base em fonte oficial."
req.scenes[4].narration = "E uma nutricionista de verdade acompanha."
req.scenes[5].narration = "NutriDeby. Sua saúde, todos os dias, no seu WhatsApp."

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

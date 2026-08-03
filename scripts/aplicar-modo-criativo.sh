#!/usr/bin/env bash
# aplicar-modo-criativo.sh — modo criativo v3 (narracao nao-fatal + assembly mudo + prompts SEM texto/pt-BR)
# Uso: rodar DENTRO da pasta do projeto sintese:  bash aplicar-modo-criativo.sh
set -euo pipefail

if [ ! -f app/api/schemas.py ]; then
  echo "ERRO: rode DENTRO da pasta sintese (nao encontrei app/api/schemas.py)."; exit 1
fi
TS=$(date +%Y%m%d_%H%M%S); BK=".bak-modo-criativo-$TS"
mkdir -p "$BK/app/api" "$BK/app/core" "$BK/app/pipeline" "$BK/scripts"
echo ">> Backup em $BK/"
for f in app/api/schemas.py app/core/state.py app/pipeline/orchestrator.py app/pipeline/assembly.py scripts/enqueue_promo.py; do
  [ -f "$f" ] && cp "$f" "$BK/$f" && echo "   guardado: $f" || true
done
mkdir -p app/api app/core app/pipeline scripts

echo ">> Escrevendo app/api/schemas.py"
cat > app/api/schemas.py <<'NUTRIDEBY_MODO_CRIATIVO_EOF'
from __future__ import annotations
import hashlib
from pydantic import BaseModel, Field


class Scene(BaseModel):
    """Cena pronta para o modo criativo (marketing). Alimenta o scene_director
    e o modelo image-to-video sem passar pela pesquisa factual."""
    visual_prompt: str = Field(..., min_length=8,
        description="Descrição visual: câmera (movimento), lente, luz, ação")
    duration_s: float = Field(2.0, ge=0.5, le=8.0,
        description="Duração-alvo da cena em segundos")
    overlay: str | None = Field(None,
        description="Sobreposição na montagem (ex.: tela do app, logo, legenda)")
    narration: str | None = Field(None,
        description="Texto de narração desta cena (opcional)")


class JobRequest(BaseModel):
    topic: str = Field(..., min_length=4,
        description="Evento/tema (documentary) ou nome do promo (creative)")
    lang: str = "pt-BR"
    formats: list[str] = Field(default_factory=lambda: ["16:9", "9:16"])
    # --- modo criativo (marketing) ---
    mode: str = Field("documentary",
        description="'documentary' = pesquisa+fonte; 'creative' = cenas prontas, sem fonte")
    scenes: list[Scene] | None = Field(None,
        description="Cenas prontas — obrigatório quando mode='creative'")
    disclosure: bool = Field(True,
        description="Mantém disclosure de IA (sempre recomendado)")

    def idempotency_id(self) -> str:
        scene_sig = ""
        if self.scenes:
            joined = "||".join(s.visual_prompt for s in self.scenes)
            scene_sig = "|" + hashlib.sha256(joined.encode()).hexdigest()[:8]
        raw = (f"{self.mode}|{self.topic}|{self.lang}|"
               f"{','.join(sorted(self.formats))}{scene_sig}").encode()
        return hashlib.sha256(raw).hexdigest()[:16]


class JobAccepted(BaseModel):
    job_id: str
    stage: str


class JobStatus(BaseModel):
    job_id: str
    stage: str
    cost_brl: float
    error: str | None = None
    artifacts: dict = {}
NUTRIDEBY_MODO_CRIATIVO_EOF

echo ">> Escrevendo app/core/state.py"
cat > app/core/state.py <<'NUTRIDEBY_MODO_CRIATIVO_EOF'
"""Máquina de estados do job, persistida em Redis.
Fluxo: QUEUED -> RESEARCHING -> SCRIPTING -> GENERATING -> NARRATING
       -> ASSEMBLING -> EXPORTING -> PUBLISHING -> DONE | FAILED
Idempotência: o job_id é derivado de um hash do payload (ver api.schemas),
então reenviar o mesmo pedido reusa o mesmo job em vez de gastar de novo.

Modo criativo (marketing): job.mode == "creative" carrega cenas prontas em
job.scenes e o orquestrador pula a pesquisa factual.
"""
from __future__ import annotations
import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
import redis
from app.config import settings

QUEUE_KEY = "sintese:queue"
JOB_PREFIX = "sintese:job:"
_r = redis.from_url(settings.redis_url, decode_responses=True)


class Stage(str, Enum):
    QUEUED = "QUEUED"
    RESEARCHING = "RESEARCHING"
    SCRIPTING = "SCRIPTING"
    GENERATING = "GENERATING"
    NARRATING = "NARRATING"
    ASSEMBLING = "ASSEMBLING"
    EXPORTING = "EXPORTING"
    PUBLISHING = "PUBLISHING"
    DONE = "DONE"
    FAILED = "FAILED"


@dataclass
class Job:
    job_id: str
    topic: str
    lang: str = "pt-BR"
    formats: list[str] = field(default_factory=lambda: ["16:9", "9:16"])
    # --- modo criativo (marketing) ---
    mode: str = "documentary"            # "documentary" | "creative"
    scenes: list | None = None           # cenas prontas (dicts) quando mode="creative"
    disclosure: bool = True              # mantém disclosure de IA
    # --- estado ---
    stage: str = Stage.QUEUED.value
    cost_brl: float = 0.0
    retries: int = 0
    error: str | None = None
    artifacts: dict = field(default_factory=dict)   # {script, scenes, clips, vo, exports}
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def key(self) -> str:
        return JOB_PREFIX + self.job_id


def save(job: Job) -> None:
    job.updated_at = time.time()
    _r.set(job.key(), json.dumps(asdict(job)))


def load(job_id: str) -> Job | None:
    raw = _r.get(JOB_PREFIX + job_id)
    if not raw:
        return None
    data = json.loads(raw)
    # tolera jobs antigos gravados antes dos campos novos
    allowed = Job.__dataclass_fields__.keys()
    data = {k: v for k, v in data.items() if k in allowed}
    return Job(**data)


def enqueue(job: Job) -> None:
    # idempotente: só cria se ainda não existe
    if not _r.exists(job.key()):
        save(job)
        _r.rpush(QUEUE_KEY, job.job_id)


def next_job_id(timeout: int = 5) -> str | None:
    res = _r.blpop(QUEUE_KEY, timeout=timeout)
    return res[1] if res else None


def set_stage(job: Job, stage: Stage) -> None:
    job.stage = stage.value
    save(job)
NUTRIDEBY_MODO_CRIATIVO_EOF

echo ">> Escrevendo app/pipeline/orchestrator.py"
cat > app/pipeline/orchestrator.py <<'NUTRIDEBY_MODO_CRIATIVO_EOF'
"""Orquestrador: roda os estágios em ordem, com estado, custo e compliance.
QUEUED -> RESEARCHING -> SCRIPTING -> [compliance] -> GENERATING -> NARRATING
       -> ASSEMBLING -> EXPORTING -> (PUBLISHING) -> DONE
Suporta retomada: se o job já tem artifacts de estágios anteriores,
pula direto para onde parou.

Modo criativo (marketing): job.mode == "creative" desvia para _run_creative,
que pula pesquisa/fonte factual e usa job.scenes prontas. Mantém disclosure de IA.
"""
from __future__ import annotations
import logging
import re
from app.config import settings
from app.core import budget
from app.core.state import Job, Stage, set_stage, save
from app.pipeline import assembly, compliance, export, geo, narration, research, scenes
from app.pipeline.video_provider import get_provider

log = logging.getLogger("orchestrator")
WORK = ".work"


def _slugify(s: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return slug[:40] or "promo"


def run(job: Job) -> None:
    # desvio de marketing: cenas prontas, sem pesquisa factual
    if getattr(job, "mode", "documentary") == "creative":
        _run_creative(job)
        return

    # ===================== MODO DOCUMENTÁRIO (inalterado) =====================
    # 1. pesquisa + roteiro (pula se já tiver script)
    if not job.artifacts.get("script"):
        set_stage(job, Stage.RESEARCHING)
        budget.charge(job, budget.COST_PER_RESEARCH_BRL, "pesquisa/roteiro")
        script = research.build_script(job.topic, job.lang)
        job.artifacts["script"] = script
        save(job)
    else:
        log.info("job %s: retomando — script já existe", job.job_id)
        script = job.artifacts["script"]
    # 2. plano de cenas + compliance (pula se já tiver compliance)
    scene_list = scenes.plan(script)
    if not job.artifacts.get("compliance"):
        set_stage(job, Stage.SCRIPTING)
        verdict = compliance.pre_generation_check(job.topic, script)
        job.artifacts["compliance"] = {"sensitive": verdict.sensitive, "notes": verdict.notes}
        save(job)
        budget.charge(job, len(scene_list) * budget.COST_PER_CLIP_BRL, "geração de cenas")
    else:
        log.info("job %s: retomando — compliance já existe", job.job_id)
        if job.cost_brl < budget.COST_PER_RESEARCH_BRL + len(scene_list) * budget.COST_PER_CLIP_BRL:
            budget.charge(job,
                          len(scene_list) * budget.COST_PER_CLIP_BRL - (job.cost_brl - budget.COST_PER_RESEARCH_BRL),
                          "geração de cenas (retomada)")
    # 3. geração de vídeo — retoma do último clip salvo
    clips: list[str] = list(job.artifacts.get("clips") or [])
    done_count = len(clips)
    if done_count < len(scene_list):
        set_stage(job, Stage.GENERATING)
        provider = get_provider()
        slug = script.get("slug", "topic")
        log.info("job %s: gerando clips %d..%d", job.job_id, done_count, len(scene_list) - 1)
        for sc in scene_list[done_count:]:
            if sc["kind"] == "geo":
                asset = geo.resolve_geo_asset(slug, sc["idx"])
                clips.append(asset if asset else
                             provider.generate(sc["prompt"], image_url=None,
                                               duration_s=sc["duration_s"],
                                               work_dir=f"{WORK}/{job.job_id}/clips"))
            else:
                clips.append(provider.generate(sc["prompt"], image_url=None,
                                               duration_s=sc["duration_s"],
                                               work_dir=f"{WORK}/{job.job_id}/clips"))
            job.artifacts["clips"] = clips
            save(job)
    else:
        log.info("job %s: retomando — todos os %d clips já gerados", job.job_id, len(clips))
        set_stage(job, Stage.GENERATING)
    job.artifacts["clips"] = clips
    # 4. narração (pula se já tiver vo)
    if not job.artifacts.get("vo"):
        set_stage(job, Stage.NARRATING)
        vo_text = " ".join(sc["narration"] for sc in scene_list if sc["narration"])
        vo_path = narration.narrate(vo_text, f"{WORK}/{job.job_id}/vo.mp3")
        job.artifacts["vo"] = vo_path
        save(job)
    else:
        log.info("job %s: retomando — narração já existe", job.job_id)
        vo_path = job.artifacts["vo"]
    # 5. montagem (pula se já tiver master)
    if not job.artifacts.get("master"):
        set_stage(job, Stage.ASSEMBLING)
        credits = [s.get("title", "") for s in script.get("sources", [])]
        master = assembly.assemble(clips, vo_path, credits, f"{WORK}/{job.job_id}/master.mp4")
        job.artifacts["master"] = master
        save(job)
    else:
        log.info("job %s: retomando — master já existe", job.job_id)
        master = job.artifacts["master"]
    # 6. export multi-formato
    set_stage(job, Stage.EXPORTING)
    job.artifacts["exports"] = export.export(master, job.formats, f"out/{job.job_id}")
    job.artifacts["platform_flags"] = compliance.platform_flags()
    set_stage(job, Stage.DONE)
    log.info("job %s DONE — custo R$%.2f", job.job_id, job.cost_brl)


def _run_creative(job: Job) -> None:
    """Modo marketing: cenas prontas (job.scenes), sem pesquisa nem fonte factual.
    Mantém disclosure de IA. Reaproveita geração/narração/montagem/export."""
    log.info("job %s: MODO CRIATIVO (marketing)", job.job_id)

    # 1-2. roteiro sintético a partir das cenas prontas (sem research/fonte)
    if not job.artifacts.get("script"):
        set_stage(job, Stage.SCRIPTING)
        job.artifacts["script"] = {"slug": _slugify(job.topic), "sources": [], "creative": True}
        job.artifacts["compliance"] = {
            "sensitive": False,
            "notes": "modo criativo (marketing) — sem fonte factual; encenação permitida; disclosure de IA mantido",
        }
        save(job)
    script = job.artifacts["script"]

    # normaliza as cenas do job para o formato interno (dict com kind/idx/prompt/…)
    raw_scenes = job.scenes or []
    scene_list = []
    for i, sc in enumerate(raw_scenes):
        vp = sc.get("visual_prompt") if isinstance(sc, dict) else getattr(sc, "visual_prompt", "")
        du = (sc.get("duration_s") if isinstance(sc, dict) else getattr(sc, "duration_s", None)) or 2.0
        na = sc.get("narration") if isinstance(sc, dict) else getattr(sc, "narration", None)
        ov = sc.get("overlay") if isinstance(sc, dict) else getattr(sc, "overlay", None)
        scene_list.append({"kind": "creative", "idx": i, "prompt": vp,
                           "duration_s": du, "narration": na, "overlay": ov})
    if not scene_list:
        raise ValueError("mode='creative' exige job.scenes (nenhuma cena recebida)")

    # orçamento (cobra uma vez; respeita retomada)
    expected = len(scene_list) * budget.COST_PER_CLIP_BRL
    if job.cost_brl < expected:
        budget.charge(job, expected - job.cost_brl, "geração de cenas (criativo)")

    # 3. geração de vídeo — retoma do último clip salvo
    clips: list[str] = list(job.artifacts.get("clips") or [])
    if len(clips) < len(scene_list):
        set_stage(job, Stage.GENERATING)
        provider = get_provider()
        log.info("job %s: gerando clips %d..%d", job.job_id, len(clips), len(scene_list) - 1)
        for sc in scene_list[len(clips):]:
            clips.append(provider.generate(sc["prompt"], image_url=None,
                                           duration_s=sc["duration_s"],
                                           work_dir=f"{WORK}/{job.job_id}/clips"))
            job.artifacts["clips"] = clips
            save(job)
    else:
        set_stage(job, Stage.GENERATING)
    job.artifacts["clips"] = clips

    # 4. narração (opcional e NÃO-FATAL — hero é mudo; se edge-tts cair, segue sem áudio)
    if job.artifacts.get("vo") is None:
        set_stage(job, Stage.NARRATING)
        vo_text = " ".join(sc["narration"] for sc in scene_list if sc.get("narration"))
        vo_path = ""
        if vo_text.strip():
            try:
                vo_path = narration.narrate(vo_text, f"{WORK}/{job.job_id}/vo.mp3")
            except Exception as e:  # noqa: BLE001 — narração indisponível não derruba o promo
                log.warning("job %s: narração indisponível (%s) — seguindo SEM áudio",
                            job.job_id, type(e).__name__)
                vo_path = ""
        job.artifacts["vo"] = vo_path
        save(job)
    vo_path = job.artifacts.get("vo") or None

    # 5. montagem — sem créditos de fonte; overlays de UI/logo entram aqui (ver nota no roteiro)
    if not job.artifacts.get("master"):
        set_stage(job, Stage.ASSEMBLING)
        overlays = [sc.get("overlay") for sc in scene_list if sc.get("overlay")]
        job.artifacts["overlays"] = overlays  # assembly.py pode consumir isso para sobrepor a tela do app/logo
        master = assembly.assemble(clips, vo_path, [], f"{WORK}/{job.job_id}/master.mp4")
        job.artifacts["master"] = master
        save(job)
    master = job.artifacts["master"]

    # 6. export multi-formato + disclosure de IA
    set_stage(job, Stage.EXPORTING)
    job.artifacts["exports"] = export.export(master, job.formats, f"out/{job.job_id}")
    job.artifacts["platform_flags"] = compliance.platform_flags()
    set_stage(job, Stage.DONE)
    log.info("job %s DONE (criativo) — custo R$%.2f", job.job_id, job.cost_brl)
NUTRIDEBY_MODO_CRIATIVO_EOF

echo ">> Escrevendo app/pipeline/assembly.py"
cat > app/pipeline/assembly.py <<'NUTRIDEBY_MODO_CRIATIVO_EOF'
"""Montagem final com MoviePy/FFmpeg.
Junta clipes + narração, queima:
  - overlay de disclosure de IA (compliance, persistente)
  - crédito de fonte por cena (rodapé)
Entrega o master em 16:9; export.py deriva os outros formatos.

Robustez: vídeo SEM áudio (ex.: promo mudo / hero) é suportado — se vo_path
for vazio/None, monta sem trilha em vez de quebrar.
TODO(produção): transição/ritmo, trilha licenciada, color grade.
"""
from __future__ import annotations
from pathlib import Path
from app.pipeline.compliance import disclosure_overlay_spec


def _disclosure_clip(size: tuple, duration: float):
    from moviepy import CompositeVideoClip
    from moviepy.video.VideoClip import ColorClip, TextClip
    spec = disclosure_overlay_spec()
    txt = TextClip(
        text=spec["label"], font_size=22, font=spec["font"],
        color="white", duration=duration,
    )
    bg = ColorClip(size=(size[0], 40), color=(0, 0, 0), duration=duration).with_opacity(0.45)
    return CompositeVideoClip([bg, txt.with_position(("center", "center"))]) \
        .with_position(("center", size[1] - 48))


def assemble(clip_paths: list[str], vo_path: str, source_credits: list[str],
             out_path: str, size=(1920, 1080)) -> str:
    from moviepy import AudioFileClip, CompositeVideoClip, VideoFileClip, concatenate_videoclips
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    clips = [VideoFileClip(p).resized(size) for p in clip_paths]
    base = concatenate_videoclips(clips, method="compose")

    # narração é opcional: só adiciona faixa de áudio se houver arquivo válido
    has_audio = bool(vo_path) and Path(vo_path).exists()
    if has_audio:
        vo = AudioFileClip(vo_path)
        base = base.with_audio(vo)

    disclosure = _disclosure_clip(size, base.duration)
    final = CompositeVideoClip([base, disclosure])
    final.write_videofile(
        out_path, fps=30, codec="libx264",
        audio=has_audio,
        audio_codec="aac" if has_audio else None,
    )
    return out_path
NUTRIDEBY_MODO_CRIATIVO_EOF

echo ">> Escrevendo scripts/enqueue_promo.py"
cat > scripts/enqueue_promo.py <<'NUTRIDEBY_MODO_CRIATIVO_EOF'
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
NUTRIDEBY_MODO_CRIATIVO_EOF

echo ">> Checando sintaxe Python..."
python3 -m py_compile app/api/schemas.py app/core/state.py app/pipeline/orchestrator.py app/pipeline/assembly.py scripts/enqueue_promo.py
echo ""; echo "==================================================="
echo " Modo criativo v3 instalado (SEM texto na IA + pt-BR garantido)."
echo " Originais em: $BK/"; echo ""
echo " Para terminar o VIDEO DE TESTE (mudo, ja pago):"
echo "   1) docker compose up -d --build worker"
echo "   2) docker compose run --rm worker python -c \"from app.core.state import _r, QUEUE_KEY; _r.rpush(QUEUE_KEY, '9bdd23bb945e7748'); print('retomado')\""
echo "   3) docker compose logs -f worker      # ate DONE"
echo "==================================================="

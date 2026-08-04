"""Cobertura do orquestrador (app/pipeline/orchestrator.py).

O que é real aqui: `scenes.plan`, `compliance`, `budget` e a máquina de estados.
O que é falseado: só o que gasta dinheiro ou toca rede/disco — provider de vídeo,
TTS, montagem, export e resolução de asset geográfico.

É esse recorte que dá valor ao teste: a retomada, o teto de custo e o bloqueio de
compliance são verificados contra a lógica de verdade, sem gerar um frame.
"""
from __future__ import annotations

import pytest

from app.core import budget, state
from app.core.errors import BudgetExceeded, ComplianceBlock
from app.core.state import Job, Stage
from app.pipeline import orchestrator

from tests.test_state import FakeRedis


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture(autouse=True)
def _redis(monkeypatch) -> FakeRedis:
    fake = FakeRedis()
    monkeypatch.setattr(state, "_r", fake)
    return fake


@pytest.fixture(autouse=True)
def _pin_settings(monkeypatch):
    """Fixa o que vem do ambiente: a suite não pode depender do .env da máquina."""
    monkeypatch.setattr(budget.settings, "job_budget_brl_max", 1000.0)
    monkeypatch.setattr(budget.settings, "job_max_scenes", 12)
    monkeypatch.setattr(budget.settings, "require_sources", True)
    monkeypatch.setattr(budget.settings, "allow_photoreal_real_event", False)


class Spy:
    """Registra o que cada estágio falseado recebeu."""

    def __init__(self) -> None:
        self.research: list[tuple[str, str]] = []
        self.generated: list[str] = []
        self.narrate: list[dict] = []
        self.assembled: list[tuple] = []
        self.exported: list[tuple] = []
        self.geo_lookups: list[tuple[str, int]] = []
        self.geo_asset: str | None = None
        self.narrate_raises = False


def make_script(n_beats: int = 3, sources: bool = True,
                kinds: list[str] | None = None) -> dict:
    kinds = kinds or ["ai_clip"] * n_beats
    return {
        "slug": "terremoto-venezuela",
        "sources": ([{"title": "USGS", "url": "https://earthquake.usgs.gov/"}]
                    if sources else []),
        "beats": [
            {"kind": kinds[i], "visual_prompt": f"cena {i}",
             "duration_s": 5, "narration": f"narração {i}", "source_ref": 0}
            for i in range(n_beats)
        ],
    }


@pytest.fixture
def spy(monkeypatch) -> Spy:
    s = Spy()
    script = make_script()

    def fake_build_script(topic: str, lang: str = "pt-BR") -> dict:
        s.research.append((topic, lang))
        return script

    class FakeProvider:
        def generate(self, prompt, image_url=None, duration_s=None, work_dir=None):
            s.generated.append(prompt)
            return f"{work_dir}/clip{len(s.generated) - 1}.mp4"

    def fake_narrate(text, out_path, voice=None, lang=None):
        if s.narrate_raises:
            raise RuntimeError("edge-tts indisponível")
        s.narrate.append({"text": text, "out": out_path, "voice": voice, "lang": lang})
        return out_path

    def fake_assemble(clips, vo, credits, out):
        s.assembled.append((tuple(clips), vo, tuple(credits), out))
        return out

    def fake_export(master, formats, out_dir):
        s.exported.append((master, tuple(formats), out_dir))
        return {f: f"{out_dir}/{f.replace(':', 'x')}.mp4" for f in formats}

    def fake_geo(slug, idx):
        s.geo_lookups.append((slug, idx))
        return s.geo_asset

    monkeypatch.setattr(orchestrator.research, "build_script", fake_build_script)
    monkeypatch.setattr(orchestrator, "get_provider", lambda: FakeProvider())
    monkeypatch.setattr(orchestrator.narration, "narrate", fake_narrate)
    monkeypatch.setattr(orchestrator.assembly, "assemble", fake_assemble)
    monkeypatch.setattr(orchestrator.export, "export", fake_export)
    monkeypatch.setattr(orchestrator.geo, "resolve_geo_asset", fake_geo)
    s.script = script
    return s


def new_job(**kw) -> Job:
    base = {"job_id": "j1", "topic": "Terremoto da Venezuela em 24/06/2026"}
    base.update(kw)
    job = Job(**base)
    state.save(job)
    return job


# --------------------------------------------------------------------------- #
# modo documentário
# --------------------------------------------------------------------------- #

def test_happy_path_percorre_todos_os_estagios(spy):
    job = new_job()

    orchestrator.run(job)

    assert job.stage == Stage.DONE.value
    assert len(spy.generated) == 3
    assert len(job.artifacts["clips"]) == 3
    assert job.artifacts["vo"]
    assert job.artifacts["master"]
    assert set(job.artifacts["exports"]) == {"16:9", "9:16"}
    assert job.artifacts["platform_flags"]["youtube_altered_content"] is True
    # 1 pesquisa + 3 clipes, com os custos reais de budget.py
    assert job.cost_brl == pytest.approx(
        budget.COST_PER_RESEARCH_BRL + 3 * budget.COST_PER_CLIP_BRL
    )


def test_credita_as_fontes_na_montagem(spy):
    """Fonte citada tem que chegar nos créditos — é requisito de compliance."""
    job = new_job()

    orchestrator.run(job)

    _clips, _vo, credits, _out = spy.assembled[0]
    assert credits == ("USGS",)


def test_marca_evento_sensivel(spy):
    """'Terremoto' é gatilho de sensibilidade: exige revisão humana."""
    job = new_job()

    orchestrator.run(job)

    assert job.artifacts["compliance"]["sensitive"] is True
    assert job.artifacts["compliance"]["notes"]


def test_estado_persistido_permite_consulta_durante_o_run(spy):
    """O job no Redis tem que refletir o progresso, não só o resultado final."""
    job = new_job()

    orchestrator.run(job)

    do_redis = state.load("j1")
    assert do_redis.stage == Stage.DONE.value
    assert len(do_redis.artifacts["clips"]) == 3
    assert do_redis.cost_brl == job.cost_brl


# --------------------------------------------------------------------------- #
# retomada — o ponto central: reiniciar worker não pode gerar custo de novo
# --------------------------------------------------------------------------- #

def test_retomada_nao_repete_a_pesquisa(spy):
    job = new_job()
    job.artifacts["script"] = spy.script
    state.save(job)

    orchestrator.run(job)

    assert spy.research == []
    assert job.stage == Stage.DONE.value


def test_retomada_gera_apenas_os_clips_faltantes(spy):
    """Com 1 de 3 clipes prontos, só os 2 restantes podem ser gerados."""
    job = new_job()
    job.artifacts["script"] = spy.script
    job.artifacts["compliance"] = {"sensitive": True, "notes": []}
    job.artifacts["clips"] = ["ja/clip0.mp4"]
    job.cost_brl = budget.COST_PER_RESEARCH_BRL + 3 * budget.COST_PER_CLIP_BRL
    state.save(job)

    orchestrator.run(job)

    assert spy.generated == ["cena 1", "cena 2"]
    assert len(job.artifacts["clips"]) == 3
    assert job.artifacts["clips"][0] == "ja/clip0.mp4"


def test_retomada_com_todos_os_clips_nao_chama_o_provider(spy):
    job = new_job()
    job.artifacts["script"] = spy.script
    job.artifacts["compliance"] = {"sensitive": True, "notes": []}
    job.artifacts["clips"] = [f"ja/clip{i}.mp4" for i in range(3)]
    job.cost_brl = budget.COST_PER_RESEARCH_BRL + 3 * budget.COST_PER_CLIP_BRL
    state.save(job)

    orchestrator.run(job)

    assert spy.generated == []
    assert job.stage == Stage.DONE.value


def test_retomada_nao_remonta_o_master(spy):
    job = new_job()
    job.artifacts["script"] = spy.script
    job.artifacts["compliance"] = {"sensitive": True, "notes": []}
    job.artifacts["clips"] = [f"ja/clip{i}.mp4" for i in range(3)]
    job.artifacts["vo"] = "ja/vo.mp3"
    job.artifacts["master"] = "ja/master.mp4"
    job.cost_brl = budget.COST_PER_RESEARCH_BRL + 3 * budget.COST_PER_CLIP_BRL
    state.save(job)

    orchestrator.run(job)

    assert spy.assembled == []
    assert spy.narrate == []
    assert job.artifacts["master"] == "ja/master.mp4"


# --------------------------------------------------------------------------- #
# guard-rails: nada pago acontece se compliance ou orçamento barrarem
# --------------------------------------------------------------------------- #

def test_compliance_bloqueia_antes_de_gastar(spy, monkeypatch):
    """Roteiro sem fonte: ComplianceBlock e nenhuma chamada ao provider."""
    sem_fonte = make_script(sources=False)
    monkeypatch.setattr(orchestrator.research, "build_script",
                        lambda topic, lang="pt-BR": sem_fonte)
    job = new_job()

    with pytest.raises(ComplianceBlock):
        orchestrator.run(job)

    assert spy.generated == []


def test_teto_de_custo_aborta_antes_do_provider(spy, monkeypatch):
    """Teto baixo: BudgetExceeded antes de gerar qualquer clipe."""
    monkeypatch.setattr(budget.settings, "job_budget_brl_max", 10.0)
    job = new_job()

    with pytest.raises(BudgetExceeded):
        orchestrator.run(job)

    assert spy.generated == []


def test_cap_de_cenas_limita_a_geracao(spy, monkeypatch):
    """job_max_scenes corta runaway: 20 beats, no máximo 5 clipes."""
    monkeypatch.setattr(budget.settings, "job_max_scenes", 5)
    monkeypatch.setattr(orchestrator.research, "build_script",
                        lambda topic, lang="pt-BR": make_script(n_beats=20))
    job = new_job()

    orchestrator.run(job)

    assert len(spy.generated) == 5


# --------------------------------------------------------------------------- #
# idioma — o job bilíngue precisa narrar na voz do idioma pedido
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("lang", ["pt-BR", "en"])
def test_narracao_recebe_o_idioma_do_job(spy, lang):
    job = new_job(lang=lang)

    orchestrator.run(job)

    assert spy.narrate[0]["lang"] == lang


def test_idioma_chega_na_pesquisa(spy):
    job = new_job(lang="en")

    orchestrator.run(job)

    assert spy.research[0][1] == "en"


# --------------------------------------------------------------------------- #
# camada geográfica
# --------------------------------------------------------------------------- #

def test_cena_geo_usa_asset_local_sem_pagar_provider(spy, monkeypatch):
    monkeypatch.setattr(orchestrator.research, "build_script",
                        lambda topic, lang="pt-BR": make_script(
                            n_beats=2, kinds=["geo", "ai_clip"]))
    spy.geo_asset = "assets/geo/terremoto-venezuela/0.mp4"
    job = new_job()

    orchestrator.run(job)

    assert spy.geo_lookups == [("terremoto-venezuela", 0)]
    assert job.artifacts["clips"][0] == "assets/geo/terremoto-venezuela/0.mp4"
    assert spy.generated == ["cena 1"]          # só a cena não-geo foi gerada


def test_cena_geo_cai_no_provider_quando_o_asset_falta(spy, monkeypatch):
    monkeypatch.setattr(orchestrator.research, "build_script",
                        lambda topic, lang="pt-BR": make_script(
                            n_beats=1, kinds=["geo"]))
    spy.geo_asset = None
    job = new_job()

    orchestrator.run(job)

    assert spy.generated == ["cena 0"]


# --------------------------------------------------------------------------- #
# modo criativo (marketing)
# --------------------------------------------------------------------------- #

def test_criativo_nao_pesquisa_e_dispensa_fonte(spy):
    job = new_job(mode="creative",
                  scenes=[{"visual_prompt": "drone sobre a cidade", "duration_s": 3,
                           "narration": "abertura"}])

    orchestrator.run(job)

    assert spy.research == []
    assert job.artifacts["script"]["creative"] is True
    assert job.artifacts["script"]["sources"] == []
    assert job.stage == Stage.DONE.value
    assert len(spy.generated) == 1


def test_criativo_exige_cenas(spy):
    job = new_job(mode="creative", scenes=None)

    with pytest.raises(ValueError, match="creative"):
        orchestrator.run(job)

    assert spy.generated == []


def test_criativo_segue_sem_audio_se_a_narracao_cair(spy):
    """Narração é opcional no promo: falha de TTS não pode derrubar o job."""
    spy.narrate_raises = True
    job = new_job(mode="creative",
                  scenes=[{"visual_prompt": "drone sobre a cidade",
                           "narration": "abertura"}])

    orchestrator.run(job)

    assert job.stage == Stage.DONE.value
    assert job.artifacts["vo"] == ""
    assert job.artifacts["master"]


def test_criativo_respeita_o_cap_de_cenas(spy, monkeypatch):
    """A trava de runaway vale nos dois modos — no criativo ela não existia."""
    monkeypatch.setattr(budget.settings, "job_max_scenes", 3)
    job = new_job(mode="creative",
                  scenes=[{"visual_prompt": f"plano {i}"} for i in range(10)])

    orchestrator.run(job)

    assert len(spy.generated) == 3
    assert len(job.artifacts["clips"]) == 3


def test_criativo_cobra_so_as_cenas_que_vai_gerar(spy, monkeypatch):
    """Cortar cena tem que cortar custo junto, senão cobra pelo que não gerou."""
    monkeypatch.setattr(budget.settings, "job_max_scenes", 3)
    job = new_job(mode="creative",
                  scenes=[{"visual_prompt": f"plano {i}"} for i in range(10)])

    orchestrator.run(job)

    assert job.cost_brl == pytest.approx(3 * budget.COST_PER_CLIP_BRL)


def test_criativo_avisa_ao_cortar_cenas(spy, monkeypatch, caplog):
    """Corte silencioso vira 'gerou tudo' na cabeça de quem operou."""
    import logging

    monkeypatch.setattr(budget.settings, "job_max_scenes", 2)
    job = new_job(mode="creative",
                  scenes=[{"visual_prompt": f"plano {i}"} for i in range(5)])

    with caplog.at_level(logging.WARNING):
        orchestrator.run(job)

    assert "cortando" in caplog.text
    assert "JOB_MAX_SCENES" in caplog.text


def test_criativo_dentro_do_cap_nao_avisa(spy, monkeypatch, caplog):
    import logging

    monkeypatch.setattr(budget.settings, "job_max_scenes", 12)
    job = new_job(mode="creative",
                  scenes=[{"visual_prompt": f"plano {i}"} for i in range(4)])

    with caplog.at_level(logging.WARNING):
        orchestrator.run(job)

    assert "cortando" not in caplog.text
    assert len(spy.generated) == 4


def test_criativo_repassa_overlays_para_a_montagem(spy):
    job = new_job(mode="creative",
                  scenes=[{"visual_prompt": "tela do app", "overlay": "logo"}])

    orchestrator.run(job)

    assert job.artifacts["overlays"] == ["logo"]

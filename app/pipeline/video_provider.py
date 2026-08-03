"""Interface VideoProvider + implementação fal.ai por POLLING (ADR-01).

Usa as URLs que o próprio fal devolve no submit (status_url/response_url),
em vez de montar o caminho na mão — o caminho de status do fal usa só o
prefixo base do modelo, não o slug completo.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.errors import ProviderTimeout

FAL_BASE = "https://queue.fal.run"


class VideoProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, image_url: str | None, duration_s: float,
                 work_dir: str = ".work/clips") -> str:
        ...


class FalProvider(VideoProvider):
    def __init__(self) -> None:
        if not settings.fal_key:
            raise RuntimeError("FAL_KEY ausente")
        self._headers = {"Authorization": f"Key {settings.fal_key}"}

    @retry(stop=stop_after_attempt(settings.job_max_retries + 1),
           wait=wait_exponential(min=2, max=20))
    def _submit(self, model: str, payload: dict) -> dict:
        with httpx.Client(timeout=60) as c:
            r = c.post(f"{FAL_BASE}/{model}", json=payload, headers=self._headers)
            r.raise_for_status()
            return r.json()  # contém request_id, status_url, response_url

    def _poll(self, status_url: str, response_url: str) -> str:
        deadline = time.time() + settings.provider_poll_timeout_s
        with httpx.Client(timeout=60) as c:
            while time.time() < deadline:
                r = c.get(status_url, headers=self._headers)
                r.raise_for_status()
                st = r.json()
                status = st.get("status")
                if status == "COMPLETED":
                    out = c.get(response_url, headers=self._headers).json()
                    return self._extract_url(out)
                if status in ("FAILED", "ERROR"):
                    raise RuntimeError(f"fal job FAILED: {st}")
                time.sleep(settings.provider_poll_interval_s)
        raise ProviderTimeout("fal job estourou o timeout")

    @staticmethod
    def _extract_url(out: dict) -> str:
        # Kling/Veo variam o formato; cobre os casos conhecidos.
        v = out.get("video")
        if isinstance(v, dict) and v.get("url"):
            return v["url"]
        if isinstance(v, str):
            return v
        vids = out.get("videos")
        if isinstance(vids, list) and vids and isinstance(vids[0], dict):
            return vids[0]["url"]
        raise RuntimeError(f"URL de vídeo não encontrada na resposta: {out}")

    @staticmethod
    def _kling_duration(duration_s: float) -> str:
        """Kling aceita somente '4s', '6s' ou '8s'."""
        if duration_s <= 5:
            return "4s"
        if duration_s <= 7:
            return "6s"
        return "8s"

    @staticmethod
    def _download(url: str, dest_dir: str) -> str:
        import hashlib
        from pathlib import Path
        Path(dest_dir).mkdir(parents=True, exist_ok=True)
        fname = hashlib.md5(url.encode()).hexdigest()[:12] + ".mp4"
        dest = str(Path(dest_dir) / fname)
        timeout = httpx.Timeout(connect=30.0, read=300.0, write=60.0, pool=30.0)
        last_err = None
        dest_p = Path(dest)
        for attempt in range(1, 4):
            try:
                with httpx.Client(timeout=timeout, follow_redirects=True) as c:
                    with c.stream("GET", url) as r:
                        r.raise_for_status()
                        tmp = dest_p.with_suffix(".part")
                        with open(tmp, "wb") as f:
                            for chunk in r.iter_bytes(chunk_size=65536):
                                f.write(chunk)
                        tmp.rename(dest_p)
                return dest
            except (httpx.HTTPError, OSError) as e:
                last_err = e
                time.sleep(5 * attempt)
        raise RuntimeError(f"download falhou apos 3 tentativas: {last_err}")

    def generate(self, prompt: str, image_url: str | None, duration_s: float,
                 work_dir: str = ".work/clips") -> str:
        model = settings.fal_model_i2v if image_url else settings.fal_model_t2v
        if not model:
            raise RuntimeError("slug do modelo fal não configurado (FAL_MODEL_*)")
        payload = {"prompt": prompt, "duration": self._kling_duration(duration_s)}
        if image_url:
            payload["image_url"] = image_url
        sub = self._submit(model, payload)
        video_url = self._poll(sub["status_url"], sub["response_url"])
        return self._download(video_url, work_dir)


def get_provider() -> VideoProvider:
    return FalProvider()

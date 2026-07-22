"""Camada geográfica — o diferencial do canal.

Earth Studio NÃO tem API pública: os voos de mapa são renderizados/exportados
manualmente (frames) e versionados em assets/geo/<slug>/. Aqui a gente apenas
resolve o asset pré-renderizado da cena e o entrega pra montagem. Se faltar,
cai num fallback de mapa estático com atribuição.

TODO(produção): pipeline de geração de frames Earth Studio + cache no Spaces.
"""
from __future__ import annotations

from pathlib import Path

GEO_ROOT = Path("assets/geo")


def resolve_geo_asset(slug: str, scene_idx: int) -> str | None:
    candidate = GEO_ROOT / slug / f"scene_{scene_idx:02d}.mp4"
    return str(candidate) if candidate.exists() else None

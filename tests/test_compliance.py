import pytest

from app.core.errors import ComplianceBlock
from app.pipeline import compliance


def test_blocks_script_without_sources():
    with pytest.raises(ComplianceBlock):
        compliance.pre_generation_check("terremoto venezuela", {"sources": []})


def test_blocks_photoreal_real_event():
    with pytest.raises(ComplianceBlock):
        compliance.pre_generation_check(
            "terremoto venezuela",
            {"sources": [{"title": "USGS"}], "photoreal_real_event": True},
        )


def test_flags_sensitive_event():
    v = compliance.pre_generation_check(
        "terremoto venezuela", {"sources": [{"title": "USGS"}]}
    )
    assert v.sensitive is True
    assert v.notes

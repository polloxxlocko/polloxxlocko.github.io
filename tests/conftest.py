"""Configuración común de pruebas: las pruebas nunca escriben en el registro real de la valla de GATE 3."""
import pytest

from qsports import paths


@pytest.fixture(autouse=True)
def _isolated_fence_log(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "FENCE_LOG", tmp_path / "GATE3_FENCE_LOG.jsonl")
    yield

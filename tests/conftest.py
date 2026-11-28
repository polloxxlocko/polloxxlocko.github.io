"""Configuración común de pruebas: las pruebas nunca escriben en el registro real de la valla de GATE 3.
Comprobación previa: pyarrow es una dependencia declarada (requirements-lock.txt, pyproject.toml); sin ella fallarían
muchas pruebas por motivos ajenos al proyecto, así que la ejecución se detiene con un mensaje claro."""
import pytest


def pytest_configure(config):
    try:
        import pyarrow  # noqa: F401
    except ImportError as e:  # pragma: no cover
        raise pytest.UsageError("Falta pyarrow, dependencia declarada del proyecto. Instale el entorno con "
                                "`pip install -r requirements-lock.txt` y `pip install -e .`") from e

from qsports import paths


@pytest.fixture(autouse=True)
def _isolated_fence_log(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "FENCE_LOG", tmp_path / "GATE3_FENCE_LOG.jsonl")
    yield

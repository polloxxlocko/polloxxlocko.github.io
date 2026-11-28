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


_REAL_RESERVED = {"holdout": paths.HOLDOUT_DIR.resolve(), "reserve": paths.RESERVE_DIR.resolve()}


@pytest.fixture(autouse=True)
def _never_open_real_reserved_data(monkeypatch):
    """Guarda (incidente I-1 de la prueba final): ninguna prueba puede abrir datos reservados REALES, aunque exista
    una autorización vigente. Solo se permite abrir particiones de proyectos temporales (rutas parcheadas)."""
    from qsports import holdout
    real_open = holdout.open_reserved

    def guarded(partition, purpose):
        if holdout._part_dir(partition).resolve() == _REAL_RESERVED.get(partition):
            raise RuntimeError(f"Las pruebas no pueden abrir datos reservados reales ({partition}).")
        return real_open(partition, purpose)
    monkeypatch.setattr(holdout, "open_reserved", guarded)
    yield

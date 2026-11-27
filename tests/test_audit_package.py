"""El verificador del paquete distingue manifiestos de hashes (permitidos) de archivos de datos (prohibidos).

Las rutas reservadas se construyen desde `holdout.RESERVED_PATH_MARKERS` para no nombrarlas aquí (tripwire).
"""
from qsports.audit_package import is_forbidden
from qsports.holdout import RESERVED_PATH_MARKERS

RAW_H, RAW_R, PROC_H, PROC_R, FULL = RESERVED_PATH_MARKERS


def test_manifests_allowed_data_forbidden():
    for raw in (RAW_H, RAW_R):
        assert not is_forbidden(f"pkg/{raw}/football_data/manifest.jsonl")
        assert is_forbidden(f"pkg/{raw}/football_data/E0/data.csv")
        assert is_forbidden(f"pkg/{raw}/football_data/x.zip")
    for proc in (PROC_H, PROC_R):
        assert is_forbidden(f"pkg/{proc}/{FULL}")
        assert is_forbidden(f"pkg/{proc}/other.parquet")
    assert is_forbidden("pkg/research/abstracts_local.json")
    assert is_forbidden("pkg/.env")
    assert not is_forbidden("pkg/experiments/gate2/predictions/M2/M2__h480_r64.parquet")
    assert not is_forbidden("pkg/src/qsports/holdout.py")

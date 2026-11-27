"""Protección del holdout y de la reserva prospectiva."""
import json
import re
from pathlib import Path

import pandas as pd
import pytest

from qsports import holdout, paths

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("code,part", [("0001", "dev"), ("2324", "dev"), ("2425", "holdout"), ("2526", "holdout"),
                                       ("2627", "reserve"), ("2728", "reserve")])
def test_partition_mapping(code, part):
    assert paths.partition_of(code) == part


def test_assert_no_reserved_rejects_reserved_seasons():
    with pytest.raises(holdout.ReservedDataError):
        holdout.assert_no_reserved(pd.DataFrame({"season_code": ["2324", "2425"]}), "test")
    with pytest.raises(holdout.ReservedDataError):
        holdout.assert_no_reserved(pd.DataFrame({"season_code": ["2627"]}), "test")
    holdout.assert_no_reserved(pd.DataFrame({"season_code": ["2223", "2324"]}), "test")


def test_assert_no_reserved_rejects_reserved_match_ids_even_if_relabelled():
    if not (paths.HOLDOUT_DIR / "registry.json").exists():
        pytest.skip("Requiere el sellado (python -m qsports build)")
    rid = holdout.registry("holdout")["match_ids"][0]
    sneaky = pd.DataFrame({"season_code": ["2324"], "match_id": [rid]})  # temporada falsificada
    with pytest.raises(holdout.ReservedDataError):
        holdout.assert_no_reserved(sneaky, "test")


def test_open_reserved_denied_in_current_project_state():
    with pytest.raises(holdout.ReservedDataError, match="SELLADA|PROTOCOL"):
        holdout.open_reserved("holdout", purpose="test")
    with pytest.raises(holdout.ReservedDataError):
        holdout.open_reserved("reserve", purpose="test")


def _fake_project(tmp_path, monkeypatch):
    (tmp_path / "configs").mkdir()
    cfg = json.loads((ROOT / "configs" / "holdout.json").read_text())
    (tmp_path / "configs" / "holdout.json").write_text(json.dumps(cfg))
    hd = tmp_path / "data" / "holdout"
    (hd / "processed").mkdir(parents=True)
    pd.DataFrame({"match_id": ["x"], "season_code": ["2425"], "fthg": [1.0]}).to_parquet(
        hd / "processed" / "matches_full.parquet")
    (tmp_path / "EXPERIMENTAL_PROTOCOL.md").write_text("protocolo v1")
    (tmp_path / "PROTOCOL_FREEZE.json").write_text(json.dumps({"files": ["EXPERIMENTAL_PROTOCOL.md"]}))
    monkeypatch.setattr(paths, "ROOT", tmp_path)
    monkeypatch.setattr(paths, "CONFIGS", tmp_path / "configs")
    monkeypatch.setattr(paths, "HOLDOUT_DIR", hd)
    return hd


def test_authorization_flow_hash_binding_and_access_log(tmp_path, monkeypatch):
    hd = _fake_project(tmp_path, monkeypatch)
    with pytest.raises(holdout.ReservedDataError):  # sin autorización
        holdout.open_reserved("holdout", "test")
    auth = {"partition": "holdout", "authorized_by": "usuario", "authorized_at": "2027-01-01",
            "user_statement": "Autorizo abrir el holdout", "purpose": "evaluación final",
            "protocol_freeze_sha256": holdout.protocol_freeze_hash()}
    (tmp_path / "HOLDOUT_AUTHORIZATION.json").write_text(json.dumps(auth))
    df = holdout.open_reserved("holdout", "evaluación final")
    assert len(df) == 1
    log = (hd / "ACCESS_LOG.jsonl").read_text().splitlines()
    assert len(log) == 1 and json.loads(log[0])["purpose"] == "evaluación final"
    # cambiar el protocolo después de autorizar invalida el acceso
    (tmp_path / "EXPERIMENTAL_PROTOCOL.md").write_text("protocolo v2 (modificado tras ver datos)")
    with pytest.raises(holdout.ReservedDataError, match="hash"):
        holdout.open_reserved("holdout", "test")


def test_incomplete_authorization_rejected(tmp_path, monkeypatch):
    _fake_project(tmp_path, monkeypatch)
    auth = {"partition": "holdout", "protocol_freeze_sha256": holdout.protocol_freeze_hash()}
    (tmp_path / "HOLDOUT_AUTHORIZATION.json").write_text(json.dumps(auth))
    with pytest.raises(holdout.ReservedDataError, match="incompleta"):
        holdout.open_reserved("holdout", "test")


FORBIDDEN = ["HOLDOUT_DIR", "RESERVE_DIR", "data/holdout", "data/reserve", "matches_full.parquet",
             "open_reserved", "_full_path"]
ALLOWED = {"src/qsports/paths.py", "src/qsports/holdout.py", "tests/test_holdout.py"}


def test_tripwire_reserved_paths():
    """Ningún módulo fuera de los autorizados puede nombrar rutas o accesos reservados."""
    offenders = []
    for d in ("src", "phase0", "tests", "experiments", "scripts", "notebooks"):
        for f in (ROOT / d).rglob("*.py") if (ROOT / d).exists() else []:
            rel = f.relative_to(ROOT).as_posix()
            if rel in ALLOWED:
                continue
            text = f.read_text(encoding="utf-8")
            for tok in FORBIDDEN:
                if tok in text:
                    offenders.append(f"{rel}: {tok}")
    assert not offenders, offenders


def test_tripwire_notebooks_do_not_read_reserved():
    for nb in ROOT.rglob("*.ipynb"):
        if ".ipynb_checkpoints" in nb.parts:
            continue
        text = nb.read_text(encoding="utf-8")
        assert not re.search(r"data/(holdout|reserve)", text), nb


def test_level0_contains_no_values():
    if not (paths.HOLDOUT_DIR / "processed" / "metadata_level0.parquet").exists():
        pytest.skip("Requiere el sellado")
    for part in ("holdout", "reserve"):
        cols = set(holdout.load_level0(part).columns)
        leaked = {c for c in cols if c in {"fthg", "ftag", "ftr", "hthg", "htag", "total_goals", "over25", "hs", "hc",
                                           "hy", "referee"} or re.search(r"_(over|under|h|d|a)$", c)}
        assert not leaked, leaked

"""GATE 2.1, exigencia 4: registro fail-closed, sello con cero accesos y autorización de GATE 3 con registro."""
import hashlib
import json

import pandas as pd
import pytest

from qsports import holdout, paths, synthetic, walkforward as wf


class Probe:
    def fit(self, train, tau):
        return {}

    def predict(self, rows):
        return [0.5] * len(rows)


# ---------------------------------------------------------------- fail-closed
def test_missing_registry_fails_closed_for_real_data(tmp_path, monkeypatch):
    monkeypatch.setattr(holdout, "_registry_path", lambda part: tmp_path / f"no_{part}.json")
    real = pd.DataFrame({"season_code": ["2324"], "match_id": ["4f1c0a9e2b7d"]})
    with pytest.raises(holdout.ReservedDataError, match="fail-closed"):
        holdout.assert_no_reserved(real, "test")
    with pytest.raises(holdout.ReservedDataError):
        holdout.reserved_ids()
    # datos sintéticos: se verifican por temporada, sin registro
    holdout.assert_no_reserved(pd.DataFrame({"season_code": ["2324"], "match_id": ["syn0123456789abc"]}), "test")
    # una sola fila real mezclada con sintéticas ya exige el registro
    mixed = pd.DataFrame({"season_code": ["2324", "2324"], "match_id": ["syn0123456789abc", "4f1c0a9e2b7d"]})
    with pytest.raises(holdout.ReservedDataError):
        holdout.assert_no_reserved(mixed, "test")


def test_inconsistent_registry_fails_closed(tmp_path, monkeypatch):
    bad = tmp_path / "reg.json"
    bad.write_text(json.dumps({"n_matches": 3, "match_ids": ["a"]}))
    monkeypatch.setattr(holdout, "_registry_path", lambda part: bad)
    with pytest.raises(holdout.ReservedDataError, match="inconsistente"):
        holdout.reserved_ids()


def test_walkforward_refuses_real_data_without_registry(tmp_path, monkeypatch):
    monkeypatch.setattr(holdout, "_registry_path", lambda part: tmp_path / "missing.json")
    s = synthetic.generate(n_divisions=1, n_teams=6, seasons=("0506",), seed=3)
    s["match_id"] = s["match_id"].str.replace("syn", "real", regex=False)
    with pytest.raises(holdout.ReservedDataError):
        wf.run(s, Probe, ["0506"], label="no-registry")


# ---------------------------------------------------------------- sello y registro de accesos
def _project(tmp_path, monkeypatch):
    for part in ("holdout", "reserve"):
        (tmp_path / part).mkdir()
    monkeypatch.setattr(holdout, "_part_dir", lambda part: tmp_path / part)
    monkeypatch.setattr(paths, "ROOT", tmp_path)


def test_sealed_state_requires_existing_empty_access_log(tmp_path, monkeypatch):
    _project(tmp_path, monkeypatch)
    st = holdout.seal_state("holdout")
    assert not st["ok"] and not st["access_log_present"]  # sin registro: no verificable -> falla
    (tmp_path / "holdout" / "ACCESS_LOG.jsonl").write_text("")
    assert holdout.seal_state("holdout")["ok"]
    (tmp_path / "holdout" / "ACCESS_LOG.jsonl").write_text(json.dumps({"partition": "holdout"}) + "\n")
    st = holdout.seal_state("holdout")
    assert not st["ok"] and st["access_log_entries"] == 1  # sellado con accesos: inconsistente


def test_current_project_is_sealed_with_zero_accesses():
    for part in ("holdout", "reserve"):
        st = holdout.seal_state(part)
        assert not st["authorization_present"]
        assert st["ok"] and st["access_log_entries"] == 0, st


# ---------------------------------------------------------------- autorización de GATE 3
def _authorize(tmp_path, cand_text="M4sport, M4cal, M2"):
    fc = wf.gate2_config()["gate3_fence"]
    cand = tmp_path / fc["frozen_candidates_file"]
    cand.parent.mkdir(parents=True, exist_ok=True)
    cand.write_text(cand_text)
    auth = {"authorized_by": "usuario (prueba)", "authorized_at": "2026-01-01", "user_statement": "prueba",
            "purpose": "prueba", "frozen_candidates_sha256": hashlib.sha256(cand.read_bytes()).hexdigest()}
    (tmp_path / fc["authorization_file"]).write_text(json.dumps(auth))
    return cand


def test_gate3_authorization_binding_and_logging(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "ROOT", tmp_path)
    s = synthetic.generate(n_divisions=1, n_teams=6, seasons=("2122", "2223"), seed=4)
    with pytest.raises(wf.FenceError, match="no está autorizado"):
        wf.run(s, Probe, ["2223"], label="sin-autorizacion")
    cand = _authorize(tmp_path)
    p, _ = wf.run(s, Probe, ["2223"], label="autorizado")
    assert len(p) > 0
    cand.write_text("candidatos modificados después de autorizar")
    with pytest.raises(wf.FenceError, match="cambiaron"):
        wf.run(s, Probe, ["2223"], label="candidatos-cambiados")
    ev = [json.loads(x) for x in paths.FENCE_LOG.read_text().splitlines()]
    assert [e["outcome"] for e in ev] == ["refused", "allowed", "refused"]
    # verify: un cruce 'allowed' sin autorización válida vigente es un fallo
    assert not wf.fence_log_summary()["ok"]


def test_incomplete_gate3_authorization_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "ROOT", tmp_path)
    _authorize(tmp_path)
    fc = wf.gate2_config()["gate3_fence"]
    a = json.loads((tmp_path / fc["authorization_file"]).read_text())
    a["user_statement"] = ""
    (tmp_path / fc["authorization_file"]).write_text(json.dumps(a))
    with pytest.raises(wf.FenceError, match="incompleta"):
        wf.check_fence(["2223"], "incompleta")


def test_real_fence_log_has_no_crossings():
    """El registro versionado no contiene cruces de la valla (las pruebas escriben en uno temporal)."""
    real = paths.ROOT / "logs" / "GATE3_FENCE_LOG.jsonl"
    assert real.exists()
    assert not [x for x in real.read_text().splitlines() if '"allowed"' in x]


def test_evaluation_universe_is_fenced_too():
    """La valla también protege la vía de evaluación (no solo el motor walk-forward)."""
    from qsports import gate2
    s = synthetic.generate(n_divisions=1, n_teams=6, seasons=("2122", "2223"), seed=4)
    with pytest.raises(wf.FenceError):
        gate2.universe(s, ["2223"])
    assert len(gate2.universe(s, ["2122"])) > 0
    ev = [json.loads(x) for x in paths.FENCE_LOG.read_text().splitlines()]
    assert ev[-1]["outcome"] == "refused" and ev[-1]["label"] == "gate2.universe"

"""GATE 4: integridad del congelamiento del protocolo de la prueba final."""
import json

import pytest

from qsports import final_test, gate2, holdout, paths


def _freeze():
    p = paths.ROOT / paths.holdout_config()["protocol_freeze_file"]
    if not p.exists():
        pytest.skip("Protocolo aún no congelado")
    return json.loads(p.read_text())


def test_frozen_files_unchanged_and_hash_stable():
    fr = _freeze()
    for f in fr["files"]:
        assert gate2.sha256_file(paths.ROOT / f) == fr["files_sha256"][f], f"archivo congelado modificado: {f}"
    assert holdout.protocol_freeze_hash() == fr["protocol_freeze_sha256_at_creation"]


def test_freeze_covers_protocol_spec_code_and_dependencies():
    files = set(_freeze()["files"])
    assert {"EXPERIMENTAL_PROTOCOL.md", "FINAL_TEST_PROTOCOL.md", "configs/final_test_frozen.json",
            "experiments/final/run_final.py", "requirements-lock.txt", "src/qsports/models.py",
            "src/qsports/final_test.py", "src/qsports/evaluation.py"} <= files
    assert {str(p.relative_to(paths.ROOT)) for p in (paths.ROOT / "src" / "qsports").glob("*.py")} <= files


def test_holdout_authorization_absent_or_bound_to_current_freeze():
    auth = paths.ROOT / paths.holdout_config()["authorization_file"]
    if not auth.exists():
        with pytest.raises(holdout.ReservedDataError):
            holdout.holdout_authorization()
    else:  # si el usuario la autoriza más adelante, debe estar ligada al congelamiento vigente
        assert holdout.holdout_authorization()["protocol_freeze_sha256"] == holdout.protocol_freeze_hash()


def test_frozen_spec_matches_gate3_candidate_and_code():
    if not final_test.spec_path().exists():
        pytest.skip("Prueba final aún no congelada")
    spec = final_test.load_spec()
    assert spec["primary"]["config_id"] == "M4cal__h730" and spec["primary_count"] == 1
    assert spec["protocol"]["sesoi_nats"] == 0.001
    assert spec["protocol"]["Q3"].startswith("NO EVALUADA")
    final_test.verify_spec(spec, require_inputs=False)

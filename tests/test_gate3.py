"""Ejecutor de GATE 3: identidad e hiperparámetros de los candidatos congelados, autorización, evaluación única."""
import copy
import json

import pandas as pd
import pytest

from qsports import gate2, gate3, paths, walkforward as wf

M2 = {"family": "M2", "config_id": "M2__h480_r64", "model": "PoissonModel",
      "constructor_args": {"half_life_days": 480, "ridge": 64.0, "max_history_days": 1460, "promoted_prior": False},
      "scope": "division", "refit_every": 1, "columns": ["home_team", "away_team", "fthg", "ftag"]}
M4C = {"family": "M4cal", "config_id": "M4cal__h730", "model": "MarketModel",
       "constructor_args": {"sport_cols": [], "ridge": 100.0, "half_life_days": 730, "require_cols": ["inp_m2"],
                            "market_col": "p_A_consensus"}, "scope": "pooled", "refit_every": 4,
       "columns": ["p_A_consensus", "over25", "inp_m2"]}
M4S = {"family": "M4sport", "config_id": "M4sport__h730_r1000", "model": "MarketModel",
       "constructor_args": {"sport_cols": ["inp_m2"], "ridge": 1000.0, "half_life_days": 730, "require_cols": ["inp_m2"],
                            "market_col": "p_A_consensus"}, "scope": "pooled", "refit_every": 4,
       "columns": ["p_A_consensus", "over25", "inp_m2"]}


@pytest.fixture()
def reference(tmp_path):
    """Reproducción de referencia mínima (manifiesto limpio, registro, resultados, entradas)."""
    ref = tmp_path / "ref"
    (ref / "predictions" / "M2").mkdir(parents=True)
    (ref / "RUN_MANIFEST.json").write_text(json.dumps({"clean": True, "git_dirty": False, "git_commit": "abc",
                                                       "code_hash": gate2.code_hash()}))
    (ref / "configs.json").write_text(json.dumps({
        "M2__h480_r64": {"params": {"half_life_days": 480, "ridge": 64, "max_history_days": 1460, "promoted_prior": False}},
        "M4cal__h730": {"params": {"half_life_days": 730, "require_cols": ["inp_m2"]}},
        "M4sport__h730_r1000": {"params": {"half_life_days": 730, "ridge": 1000.0, "sport_cols": ["inp_m2"],
                                           "require_cols": ["inp_m2"]}}}))
    (ref / "results.json").write_text(json.dumps({
        "poisson_tuning": {"M2_selected": "M2__h480_r64"},
        "m4": {"M4cal_selected": "M4cal__h730", "M4sport_selected": "M4sport__h730_r1000", "sport_cols": ["inp_m2"]}}))
    inp = ref / "predictions" / "M2" / "M2__h480_r64__inner.parquet"
    pd.DataFrame({"match_id": ["a"], "p_over": [0.5]}).to_parquet(inp)
    cfg = wf.gate2_config()
    frozen = {"reference_run": {"dir": str(ref), "git_commit": "abc"}, "code_hash": gate2.code_hash(),
              "candidates": {"M2": copy.deepcopy(M2), "M4cal": copy.deepcopy(M4C), "M4sport": copy.deepcopy(M4S)},
              "input_files_sha256": {str(inp): gate2.sha256_file(inp)},
              "protocol": {"sesoi_nats": cfg["sesoi_nats"], "bootstrap": {"week_mode": "calendar"}}}
    return frozen, ref, inp


def test_valid_frozen_candidates_pass(reference):
    frozen, _, _ = reference
    rep = gate3.verify_frozen(frozen, require_authorization=False)
    assert rep["candidates"] == {"M2": "M2__h480_r64", "M4cal": "M4cal__h730", "M4sport": "M4sport__h730_r1000"}


@pytest.mark.parametrize("mutate,match", [
    (lambda f, r, i: f["candidates"]["M4sport"]["constructor_args"].__setitem__("ridge", 100.0), "ridge"),
    (lambda f, r, i: f["candidates"]["M2"]["constructor_args"].__setitem__("half_life_days", 240), "half_life_days"),
    (lambda f, r, i: f["candidates"]["M2"].__setitem__("config_id", "M2__h240_r16"), "seleccionado"),
    (lambda f, r, i: f["candidates"]["M4sport"]["constructor_args"].__setitem__("sport_cols", ["inp_m2", "inp_m3"]),
     "sport_cols"),
    (lambda f, r, i: f["candidates"]["M2"].__setitem__("model", "LogisticFeatureModel"), "Clase"),
    (lambda f, r, i: f["candidates"]["M2"]["constructor_args"].__setitem__("window_days", 365), "registro"),
    (lambda f, r, i: f["candidates"]["M4cal"]["constructor_args"].__setitem__("ridge", 5.0), "registro"),
    (lambda f, r, i: f.__setitem__("code_hash", "0" * 64), "código"),
    (lambda f, r, i: pd.DataFrame({"match_id": ["a"], "p_over": [0.51]}).to_parquet(i), "alterada"),
    (lambda f, r, i: (r / "RUN_MANIFEST.json").write_text(json.dumps({"clean": False, "git_dirty": False})), "limpia"),
    (lambda f, r, i: f["candidates"].pop("M4cal"), "Candidatos"),
])
def test_identity_and_hyperparameter_tampering_detected(reference, mutate, match):
    frozen, ref, inp = reference
    mutate(frozen, ref, inp)
    with pytest.raises((gate3.CandidateIdentityError, TypeError, ValueError), match=match):
        gate3.verify_frozen(frozen, require_authorization=False)


def test_authorization_required(reference, tmp_path, monkeypatch):
    frozen, _, _ = reference
    monkeypatch.setattr(paths, "ROOT", tmp_path / "sin_autorizacion")  # hermética
    with pytest.raises(wf.FenceError):
        gate3.verify_frozen(frozen, require_authorization=True)


def test_build_factory_checks_attributes():
    fac = gate3.build_factory(M4S)
    m = fac()
    assert m.ridge == 1000.0 and m.sport_cols == ["inp_m2"] and m.half_life_days == 730
    bad = copy.deepcopy(M2)
    bad["constructor_args"]["learning_rate"] = 0.1
    with pytest.raises(gate3.CandidateIdentityError, match="no reconocidos"):
        gate3.build_factory(bad)


def test_single_evaluation_guards(tmp_path, monkeypatch):
    out = tmp_path / "ya_existe"
    out.mkdir()
    with pytest.raises(gate3.SingleEvaluationError):
        gate3.run(out)
    seal = tmp_path / "GATE3_EVALUATED.json"
    seal.write_text("{}")
    monkeypatch.setattr(gate3, "seal_path", lambda: seal)
    with pytest.raises(gate3.SingleEvaluationError):
        gate3.run(tmp_path / "nuevo")


def test_freeze_never_overwrites(tmp_path):
    f = tmp_path / "frozen.json"
    f.write_text("{}")
    with pytest.raises(gate3.SingleEvaluationError):
        gate3.freeze(tmp_path, out=f)


def test_frozen_file_excluded_from_code_hash(tmp_path, monkeypatch):
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs" / "gate2.json").write_text("{}")
    (tmp_path / "configs" / "gate3_frozen_candidates.json").write_text("{}")
    monkeypatch.setattr(paths, "ROOT", tmp_path)
    files = gate2.code_files()
    assert "configs/gate2.json" in files and "configs/gate3_frozen_candidates.json" not in files

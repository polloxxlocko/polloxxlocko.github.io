"""Ejecutor de la prueba final: probado EXCLUSIVAMENTE con datos sintéticos (exigencia de GATE 4).

Un proyecto temporal con protocolo congelado y autorización ficticia sustituye al real; el holdout real nunca
se abre. La prueba de modo real solo comprueba que, sin autorización, el ejecutor se niega antes de cargar nada.
"""
import copy
import json

import pandas as pd
import pytest

from qsports import benchmark, final_test, gate3, holdout, paths, synthetic, walkforward as wf

G3 = json.loads((paths.ROOT / gate3.FROZEN_REL).read_text())["candidates"]  # leído antes de cambiar ROOT


def synth_spec(n_boot=300):
    return {"holdout_seasons": ["2425", "2526"], "primary": copy.deepcopy(G3["M4cal"]), "primary_count": 1,
            "auxiliary_M2": copy.deepcopy(G3["M2"]), "dataset": {},
            "protocol": {"sesoi_nats": 0.001,
                         "bootstrap": {"week_mode": "calendar", "block_weeks": 4, "n_boot": n_boot, "seed": 1},
                         "sensitivity_block_weeks": [2, 4],
                         "q2_conditions": {"validation_M4cal_minus_A_mean": -0.0004, "calibration_slope_tolerance": 0.2,
                                           "calibration_intercept_tolerance": 0.05}}}


class SyntheticData:
    """Mundo sintético con desarrollo (≤ 2021/22) y 'holdout' (2024/25-2025/26); misma interfaz que RealData."""

    def __init__(self, spec, seed=5):
        df = synthetic.generate(n_divisions=2, n_teams=10, seasons=("1819", "1920", "2021", "2122", "2425", "2526"),
                                seed=seed)
        self.dev = df[df.season_code <= "2122"].reset_index(drop=True)
        self.hold = df[df.season_code >= "2425"].reset_index(drop=True)
        b = benchmark.market_benchmarks(self.dev)
        b["p_C_hist_freq"] = benchmark.historical_frequency(self.dev)
        b["season_code"], b["div"] = self.dev["season_code"].values, self.dev["div"].values
        self.bench = b
        spec["dataset"] = {"dev_matches_content_sha256": holdout.content_hash(self.dev),
                           "dev_benchmarks_content_sha256": holdout.content_hash(self.bench)}
        self.expected_hold = holdout.content_hash(self.hold)
        base = final_test.base_from(self.dev, self.bench)
        m2, m4 = spec["auxiliary_M2"], spec["primary"]
        p2, _ = wf.run(base, gate3.build_factory(m2), ["1920", "2021", "2122"], scope="division", label="syn-M2")
        self.inp = p2[["match_id", "p_over"]].rename(columns={"p_over": "inp_m2"})
        r2, _ = wf.run(base, gate3.build_factory(m2), ["2122"], scope="division", label="syn-ref-M2")
        fr = base.merge(self.inp, on="match_id", how="left", validate="one_to_one")
        r4, _ = wf.run(fr, gate3.build_factory(m4), ["2122"], scope="pooled", refit_every=4, label="syn-ref-M4",
                       columns=m4["columns"])
        self.ref = {"seasons": ["2122"], "inp_m2": self.inp,
                    "preds": {"M2": r2[["match_id", "p_over"]], "M4cal": r4[["match_id", "p_over"]]}}
        self.holdout_loaded = False

    def dev_frames(self):
        return self.dev, self.bench

    def dev_inp_m2(self):
        return self.inp

    def identity_reference(self):
        return self.ref

    def load_holdout(self, purpose):
        self.holdout_loaded = True
        return self.hold, self.expected_hold


@pytest.fixture()
def fake_project(tmp_path, monkeypatch):
    (tmp_path / "PROTO.md").write_text("protocolo final congelado (sintético)")
    (tmp_path / "PROTOCOL_FREEZE.json").write_text(json.dumps({"files": ["PROTO.md"]}))
    monkeypatch.setattr(paths, "ROOT", tmp_path)
    auth = {"partition": "holdout", "authorized_by": "prueba", "authorized_at": "2026-01-01",
            "user_statement": "autorizo (prueba sintética)", "purpose": "prueba",
            "protocol_freeze_sha256": holdout.protocol_freeze_hash()}
    (tmp_path / paths.holdout_config()["authorization_file"]).write_text(json.dumps(auth))
    return tmp_path


@pytest.fixture(scope="module")
def world():
    spec = synth_spec()
    return spec, SyntheticData(spec)


def test_end_to_end_synthetic_single_evaluation(fake_project, world):
    spec, data = world
    rep = final_test.run_final(fake_project / "final", data=data, spec=spec, verify_repo=False)
    e = rep["evaluation"]
    assert e["coverage"]["M4cal"]["missing"] == 0 and e["n"] > 300
    assert rep["identity_replay"]["M2"]["not_equal"] == 0 and rep["identity_replay"]["M4cal"]["not_equal"] == 0
    assert e["verdicts"]["Q3"]["verdict"] == "NO EVALUADA"
    assert e["comparisons"]["Q1"]["comparison"] == "M4cal-C" and e["comparisons"]["Q2"]["comparison"] == "M4cal-A"
    assert set(e["q2_conditions"]) == {"1_direccion_en_validacion", "2_calibracion_en_holdout", "3_modelo_primario_unico"}
    lv = e["comparisons"]["Q2"]["levels"]
    assert lv["profitability"].startswith("NO EVALUADA")
    assert (fake_project / "final" / "results.json").exists() and final_test.seal_path().exists()
    outs = [json.loads(x)["outcome"] for x in paths.FENCE_LOG.read_text().splitlines()]
    assert outs.count("allowed-holdout") == 3 and "refused" not in outs  # M2 auxiliar, M4-cal y universo
    with pytest.raises(gate3.SingleEvaluationError):
        final_test.run_final(fake_project / "otra", data=data, spec=spec, verify_repo=False)


def test_refuses_without_authorization_before_loading_holdout(tmp_path, monkeypatch, world):
    spec, data = world
    monkeypatch.setattr(paths, "ROOT", tmp_path)
    data.holdout_loaded = False
    with pytest.raises(holdout.ReservedDataError):
        final_test.run_final(tmp_path / "final", data=data, spec=spec, verify_repo=False)
    assert not data.holdout_loaded and not (tmp_path / "final").exists()


def test_holdout_hash_mismatch_refused(fake_project):
    spec = synth_spec()
    data = SyntheticData(spec, seed=6)
    data.hold.loc[0, "fthg"] = data.hold.loc[0, "fthg"] + 1  # dato distinto del sellado
    with pytest.raises(final_test.DatasetHashError):
        final_test.run_final(fake_project / "final", data=data, spec=spec, verify_repo=False)
    assert not (fake_project / "final").exists() and not final_test.seal_path().exists()


def test_dev_hash_mismatch_refused(fake_project):
    spec = synth_spec()
    data = SyntheticData(spec, seed=7)
    spec["dataset"]["dev_matches_content_sha256"] = "0" * 64
    with pytest.raises(final_test.DatasetHashError):
        final_test.run_final(fake_project / "final", data=data, spec=spec, verify_repo=False)
    assert not data.holdout_loaded


def test_identity_replay_detects_different_model(fake_project):
    spec = synth_spec()
    data = SyntheticData(spec, seed=8)
    p = data.ref["preds"]["M4cal"].copy()
    p.loc[p.index[0], "p_over"] = p.loc[p.index[0], "p_over"] + 1e-12
    data.ref["preds"]["M4cal"] = p
    with pytest.raises(final_test.FinalTestError, match="identidad"):
        final_test.run_final(fake_project / "final", data=data, spec=spec, verify_repo=False)
    assert not data.holdout_loaded


@pytest.mark.parametrize("cat,conds,expected", [
    ("S-R", {"a": True, "b": True}, "AFIRMATIVO"), ("S-NR", {"a": True}, "AFIRMATIVO"),
    ("S-NR", {"a": True, "b": False}, "VENTAJA ESTADÍSTICA NO DEMOSTRADA"),
    ("EQ", {"a": True}, "VENTAJA ESTADÍSTICA NO DEMOSTRADA"), ("I-R", {"a": True}, "VENTAJA ESTADÍSTICA NO DEMOSTRADA"),
    ("INC", {"a": True}, "VENTAJA ESTADÍSTICA NO DEMOSTRADA / EVIDENCIA INSUFICIENTE"),
])
def test_q2_verdict_table(cat, conds, expected):
    assert final_test.q2_verdict(cat, conds)["verdict"] == expected


def test_q1_verdicts_and_superiority_levels():
    assert final_test.q1_verdict("S-R")["verdict"] == "AFIRMATIVO"
    assert final_test.q1_verdict("EQ")["verdict"] == "NEGATIVO"
    assert final_test.q1_verdict("INC")["verdict"] == "EVIDENCIA INSUFICIENTE"
    lv = final_test.superiority_levels(-0.0008, -0.0002, 0.001)
    assert lv["statistical_superiority"] and not lv["relevant_superiority"]
    lv = final_test.superiority_levels(-0.003, -0.0015, 0.001)
    assert lv["statistical_superiority"] and lv["relevant_superiority"]


def test_real_mode_refuses_without_authorization_and_logs_no_access(tmp_path):
    """Modo real (repositorio verdadero, sin HOLDOUT_AUTHORIZATION.json): se niega y no registra ningún acceso."""
    before = holdout.access_log_entries("holdout")
    with pytest.raises(holdout.ReservedDataError):
        final_test.run_final(tmp_path / "final")
    assert holdout.access_log_entries("holdout") == before
    assert not (tmp_path / "final").exists() and not final_test.seal_path().exists()


def test_real_frozen_spec_identity_checks():
    """Comprobaciones de identidad contra el repositorio real (sin datos). Se omite si aún no está congelada."""
    if not final_test.spec_path().exists():
        pytest.skip("Prueba final aún no congelada")
    spec = final_test.load_spec()
    final_test.verify_spec(spec, require_inputs=False)
    for mutate in (lambda s: s["primary"]["constructor_args"].__setitem__("half_life_days", 365),
                   lambda s: s["protocol"].__setitem__("sesoi_nats", 0.002),
                   lambda s: s.__setitem__("code_hash", "0" * 64),
                   lambda s: s["model_files_sha256"].__setitem__("src/qsports/models.py", "0" * 64),
                   lambda s: s.__setitem__("holdout_seasons", ["2425"])):
        bad = copy.deepcopy(spec)
        mutate(bad)
        with pytest.raises(final_test.FinalTestError):
            final_test.verify_spec(bad, require_inputs=False)

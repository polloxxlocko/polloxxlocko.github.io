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
        self.expected_hold = holdout.content_hash(self.hold)
        self.registry_hash = self.expected_hold  # "registro" sintético coherente con los datos
        spec["dataset"] = {"dev_matches_content_sha256": holdout.content_hash(self.dev),
                           "dev_benchmarks_content_sha256": holdout.content_hash(self.bench),
                           "holdout_full_content_sha256_sealed": self.expected_hold}
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

    def registry_holdout_hash(self):
        return self.registry_hash

    def load_holdout(self, purpose):
        self.holdout_loaded = True
        return self.hold, self.registry_hash


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
    assert [x["state"] for x in final_test.read_states()] == ["started", "opened", "finished"]
    assert final_test.attempt_path().exists()
    assert rep["holdout_dataset"]["matches_registry"] and rep["holdout_dataset"]["matches_frozen_spec"]
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
    """Datos cargados distintos del registro y de la especificación: se rechaza; el intento queda consumido
    (el holdout llegó a cargarse) y registrado como interrumpido."""
    spec = synth_spec()
    data = SyntheticData(spec, seed=6)
    data.hold.loc[0, "fthg"] = data.hold.loc[0, "fthg"] + 1  # dato distinto del sellado
    with pytest.raises(final_test.DatasetHashError):
        final_test.run_final(fake_project / "final", data=data, spec=spec, verify_repo=False)
    assert not (fake_project / "final").exists() and not final_test.seal_path().exists()
    assert [x["state"] for x in final_test.read_states()] == ["started", "interrupted"]
    assert final_test.attempt_path().exists()


def test_registry_and_data_agree_but_differ_from_frozen_spec(fake_project):
    """Exigencia A: dataset y registro coinciden entre sí pero difieren de la especificación congelada -> rechazo,
    ANTES de abrir el holdout y sin consumir el intento."""
    spec = synth_spec()
    data = SyntheticData(spec, seed=10)
    data.hold.loc[0, "fthg"] = data.hold.loc[0, "fthg"] + 1
    data.registry_hash = holdout.content_hash(data.hold)  # registro coherente con los datos alterados
    with pytest.raises(final_test.DatasetHashError, match="especificación congelada"):
        final_test.run_final(fake_project / "final", data=data, spec=spec, verify_repo=False)
    assert not data.holdout_loaded and not final_test.attempt_path().exists() and not final_test.read_states()


def test_loaded_data_must_match_frozen_spec_even_if_registry_changes_during_load(fake_project):
    """Si el registro coincide con la especificación antes de abrir pero los datos cargados y el registro devuelto en
    la carga coinciden entre sí y no con la especificación, también se rechaza."""
    spec = synth_spec()
    data = SyntheticData(spec, seed=11)
    alt = data.hold.copy()
    alt.loc[0, "fthg"] = alt.loc[0, "fthg"] + 1

    def load(purpose):
        data.holdout_loaded = True
        return alt, holdout.content_hash(alt)
    data.load_holdout = load
    with pytest.raises(final_test.DatasetHashError):
        final_test.run_final(fake_project / "final", data=data, spec=spec, verify_repo=False)
    assert final_test.attempt_path().exists()


def test_interruption_after_opening_blocks_second_attempt(fake_project, monkeypatch):
    """Exigencia B: interrupción entre la apertura y el sello -> estados started/opened/interrupted, marcador
    persistente, sin resultados ni sello; un segundo intento se rechaza antes de cargar nada."""
    spec = synth_spec()
    data = SyntheticData(spec, seed=12)

    def boom(*a, **k):
        raise KeyboardInterrupt("interrupción simulada")
    with monkeypatch.context() as m:
        m.setattr(final_test, "combined_frame", boom)
        with pytest.raises(KeyboardInterrupt):
            final_test.run_final(fake_project / "final", data=data, spec=spec, verify_repo=False)
    states = final_test.read_states()
    assert [x["state"] for x in states] == ["started", "opened", "interrupted"]
    assert states[-1]["error"] == "KeyboardInterrupt"
    assert final_test.attempt_path().exists()
    assert not (fake_project / "final").exists() and not final_test.seal_path().exists()
    data.holdout_loaded = False
    with pytest.raises(gate3.SingleEvaluationError):
        final_test.run_final(fake_project / "segundo", data=data, spec=spec, verify_repo=False)
    assert not data.holdout_loaded


def test_interruption_during_loading_blocks_second_attempt(fake_project):
    spec = synth_spec()
    data = SyntheticData(spec, seed=13)

    def fail(purpose):
        data.holdout_loaded = True
        raise RuntimeError("fallo de E/S simulado durante la carga")
    data.load_holdout = fail
    with pytest.raises(RuntimeError):
        final_test.run_final(fake_project / "final", data=data, spec=spec, verify_repo=False)
    assert [x["state"] for x in final_test.read_states()] == ["started", "interrupted"]
    with pytest.raises(gate3.SingleEvaluationError):
        final_test.run_final(fake_project / "final", data=SyntheticData(synth_spec(), seed=13), spec=spec,
                             verify_repo=False)


def test_concurrent_attempt_refused_and_claim_is_exclusive(fake_project):
    """Un marcador existente (p. ej. otra ejecución en curso) impide empezar; la creación es exclusiva."""
    spec = synth_spec()
    data = SyntheticData(spec, seed=14)
    final_test.claim_attempt({"simulado": "ejecución concurrente"})
    with pytest.raises(gate3.SingleEvaluationError):
        final_test.claim_attempt({"segundo": True})
    with pytest.raises(gate3.SingleEvaluationError):
        final_test.run_final(fake_project / "final", data=data, spec=spec, verify_repo=False)
    assert not data.holdout_loaded


def test_failure_before_opening_does_not_consume_the_attempt(fake_project):
    """Un error de configuración detectado antes de abrir (hash de desarrollo) no crea el marcador: el intento
    solo se consume al abrir el holdout."""
    spec = synth_spec()
    data = SyntheticData(spec, seed=15)
    good = spec["dataset"]["dev_matches_content_sha256"]
    spec["dataset"]["dev_matches_content_sha256"] = "0" * 64
    with pytest.raises(final_test.DatasetHashError):
        final_test.run_final(fake_project / "final", data=data, spec=spec, verify_repo=False)
    assert not final_test.attempt_path().exists() and not final_test.read_states()
    spec["dataset"]["dev_matches_content_sha256"] = good
    rep = final_test.run_final(fake_project / "final", data=data, spec=spec, verify_repo=False)
    assert rep["evaluation"]["verdicts"]["Q3"]["verdict"] == "NO EVALUADA"


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
    assert not final_test.attempt_path().exists() and not final_test.state_log_path().exists()


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
                   lambda s: s.__setitem__("holdout_seasons", ["2425"]),
                   lambda s: s["dataset"].__setitem__("holdout_full_content_sha256_sealed", "0" * 64)):
        bad = copy.deepcopy(spec)
        mutate(bad)
        with pytest.raises(final_test.FinalTestError):
            final_test.verify_spec(bad, require_inputs=False)

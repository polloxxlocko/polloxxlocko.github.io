"""GATE 2.1, exigencia 1: la existencia de predicciones no basta; solo se reutiliza una salida con manifiesto
de completitud válido (misma clave de caché y mismo SHA-256)."""
from functools import partial

import pandas as pd
import pytest

from qsports import gate2, models, synthetic, walkforward as wf

SEAS = ["0607"]


@pytest.fixture()
def rundir(tmp_path, monkeypatch):
    monkeypatch.setattr(gate2, "OUT", gate2.OUT)
    monkeypatch.setattr(gate2, "_RUN", dict(gate2._RUN))
    gate2.configure(tmp_path / "run", "clean")
    return tmp_path / "run"


@pytest.fixture(scope="module")
def frame():
    return synthetic.generate(n_divisions=1, n_teams=8, seasons=("0506", "0607"), seed=12)


def _run(frame):
    return gate2.run_config("M0a_test", "M0a__w365", {"window_days": 365}, partial(models.FreqModel, window_days=365),
                            frame, SEAS, "tuning", "division", 1, columns=["over25"])


def _forbid_recompute(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("se recalculó una salida que debía reutilizarse")
    monkeypatch.setattr(wf, "run", boom)


def test_published_directory_is_read_only(tmp_path, monkeypatch):
    monkeypatch.setattr(gate2, "OUT", gate2.OUT)
    with pytest.raises(gate2.ReadOnlyError):
        gate2.configure(gate2.PUBLISHED, "resume")


def test_clean_mode_requires_empty_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(gate2, "OUT", gate2.OUT)
    monkeypatch.setattr(gate2, "_RUN", dict(gate2._RUN))
    d = tmp_path / "x"
    d.mkdir()
    (d / "old_predictions.parquet").write_text("x")
    with pytest.raises(SystemExit):
        gate2.configure(d, "clean")


def test_reuse_only_with_valid_manifest(rundir, frame, monkeypatch):
    p1 = _run(frame)
    pf = rundir / "predictions" / "M0a_test" / "M0a__w365__tuning.parquet"
    assert pf.exists() and pf.with_suffix(".json").exists()
    gate2._RUN["mode"] = "resume"
    with monkeypatch.context() as m:  # manifiesto válido -> se reutiliza
        _forbid_recompute(m)
        pd.testing.assert_frame_equal(_run(frame).reset_index(drop=True), p1.reset_index(drop=True))
    # sin manifiesto (p. ej. ejecución interrumpida): las predicciones existentes NO se reutilizan
    pf.with_suffix(".json").unlink()
    assert gate2.load_preds("M0a_test").empty
    with monkeypatch.context() as m:
        _forbid_recompute(m)
        with pytest.raises(AssertionError, match="recalculó"):
            _run(frame)
    _run(frame)
    assert pf.with_suffix(".json").exists()


def test_tampered_or_stale_outputs_are_recomputed(rundir, frame, monkeypatch):
    _run(frame)
    gate2._RUN["mode"] = "resume"
    pf = rundir / "predictions" / "M0a_test" / "M0a__w365__tuning.parquet"
    df = pd.read_parquet(pf)
    df.loc[0, "p_over"] = 0.123
    df.to_parquet(pf, index=False)  # contenido alterado: el SHA-256 ya no coincide
    with monkeypatch.context() as m:
        _forbid_recompute(m)
        with pytest.raises(AssertionError, match="recalculó"):
            _run(frame)
    _run(frame)
    f2 = frame.copy()
    f2.loc[f2.index[5], "over25"] = 1 - f2.loc[f2.index[5], "over25"]  # datos de entrada distintos -> otra clave
    with monkeypatch.context() as m:
        _forbid_recompute(m)
        with pytest.raises(AssertionError, match="recalculó"):
            _run(f2)


def test_feature_cache_validated_and_isolated(rundir, monkeypatch):
    from qsports import features
    base = synthetic.generate(n_divisions=1, n_teams=8, seasons=("0506", "0607"), seed=13)
    for c in ("hs", "as_", "hst", "ast", "hc", "ac"):
        assert c in base.columns
    f1 = gate2.feature_frame(base, 5)
    assert (rundir / "features" / "team_ewm_hl5.parquet").exists()  # dentro del directorio de la ejecución
    gate2._RUN["mode"] = "resume"
    calls = []
    real = features.build_features
    monkeypatch.setattr(features, "build_features", lambda *a, **k: calls.append(1) or real(*a, **k))
    f2 = gate2.feature_frame(base, 5)
    assert not calls
    pd.testing.assert_frame_equal(f1, f2)
    b2 = base.copy()
    b2.loc[b2.index[3], "fthg"] = b2.loc[b2.index[3], "fthg"] + 1
    gate2.feature_frame(b2, 5)
    assert calls == [1]  # entrada distinta -> se recalcula


def test_load_preds_rejects_duplicates(rundir, frame):
    _run(frame)
    pf = rundir / "predictions" / "M0a_test" / "M0a__w365__tuning.parquet"
    dup = pd.concat([pd.read_parquet(pf)] * 2)
    dup.to_parquet(rundir / "predictions" / "M0a_test" / "copy.parquet", index=False)
    # sin manifiesto el archivo duplicado se ignora; con un manifiesto falso igualmente se detectaría
    assert len(gate2.load_preds("M0a_test")) == len(pd.read_parquet(pf))


def test_train_max_date_stored_per_fit_and_joinable(rundir, frame):
    """Documentación (exigencia 6): train_max_date se guarda en los fitlogs; cada predicción persistida se enlaza
    con exactamente un ajuste por (config_id, block, scope = división, fit_tau) y train_max_date < fit_tau."""
    _run(frame)
    P, L = gate2.load_preds("M0a_test"), gate2.load_fitlogs("M0a_test")
    assert "train_max_date" not in P.columns and "train_max_date" in L.columns
    P = P.merge(frame[["match_id", "div"]], on="match_id", validate="one_to_one")
    P["fit_tau"] = pd.to_datetime(P["fit_tau"]).dt.strftime("%Y-%m-%d")
    j = P.merge(L, left_on=["config_id", "block", "div", "fit_tau"], right_on=["config_id", "block", "scope", "fit_tau"],
                how="left", validate="many_to_one")
    assert j["train_max_date"].notna().all()
    assert (pd.to_datetime(j["train_max_date"]) < pd.to_datetime(j["fit_tau"])).all()


def test_clean_mode_reuses_only_its_own_outputs(rundir, frame, monkeypatch):
    """En modo limpio no se lee nada anterior (directorio vacío), pero una configuración ya calculada y validada en
    la MISMA ejecución (p. ej., al extender la grilla) se reutiliza en lugar de recalcularse."""
    assert gate2._RUN["mode"] == "clean"
    p1 = _run(frame)
    with monkeypatch.context() as m:
        _forbid_recompute(m)
        pd.testing.assert_frame_equal(_run(frame).reset_index(drop=True), p1.reset_index(drop=True))

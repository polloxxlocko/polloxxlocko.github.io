"""Motor walk-forward y features: garantías anti-filtración (exigencia 5)."""
import json

import numpy as np
import pandas as pd
import pytest

from qsports import paths, features, holdout, synthetic, walkforward as wf

POST = ["fthg", "ftag", "over25", "total_goals", "hs", "as_", "hst", "ast", "hc", "ac",
        "ou_close_avg_over", "ou_close_avg_under", "true_p_over"]


@pytest.fixture(scope="module")
def syn():
    return synthetic.generate(n_divisions=2, n_teams=10, seasons=("0506", "0607", "0708"), seed=3)


class Probe:
    """Modelo sonda: registra lo que recibe y predice la tasa histórica de su entrenamiento."""
    seen: list = []

    def fit(self, train, tau):
        Probe.seen.append(("fit", tau, train["match_date"].max(), len(train)))
        self.rate = train["over25"].mean() if len(train) else 0.5
        return {"converged": True, "iterations": 1}

    def predict(self, rows):
        Probe.seen.append(("predict", set(rows.columns)))
        return np.full(len(rows), self.rate)


class Cheater(Probe):
    def predict(self, rows):
        return rows["fthg"].to_numpy()  # debe fallar: columna post-partido retirada


def test_training_rows_strictly_before_tau_and_prematch_only(syn):
    Probe.seen = []
    preds, logs = wf.run(syn, Probe, ["0607", "0708"], scope="division", label="probe")
    fits = [s for s in Probe.seen if s[0] == "fit"]
    assert fits and all(s[2] < s[1] for s in fits if s[3] > 0)
    for s in [s for s in Probe.seen if s[0] == "predict"]:
        assert not (s[1] & set(POST)), s[1] & set(POST)
    assert (pd.to_datetime(preds["train_max_date"]) < preds["fit_tau"]).all()
    assert preds["match_id"].is_unique and len(logs) > 0


def test_postmatch_columns_unavailable_at_predict(syn):
    with pytest.raises(KeyError):
        wf.run(syn, Cheater, ["0607"], scope="pooled", label="cheat")


def test_fit_never_after_capture_and_refit_schedule(syn):
    preds, logs = wf.run(syn, Probe, ["0607", "0708"], scope="pooled", refit_every=4, label="probe4")
    m = preds.merge(syn[["match_id", "pre_odds_capture_date_est"]], on="match_id")
    assert (m["fit_tau"] <= m["pre_odds_capture_date_est"]).all()
    n_caps = syn[syn.season_code.isin(["0607", "0708"])]["pre_odds_capture_date_est"].nunique()
    assert len(logs) == int(np.ceil(n_caps / 4))


def test_fence_blocks_validation_block_and_logs_attempt(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "ROOT", tmp_path)  # hermética: sin autorización de GATE 3, sea cual sea el proyecto
    s = synthetic.generate(n_divisions=1, n_teams=6, seasons=("2122", "2223"), seed=4)
    with pytest.raises(wf.FenceError):
        wf.run(s, Probe, ["2223"], label="fence")
    wf.run(s, Probe, ["2122"], label="fence-ok")
    ev = [json.loads(x) for x in paths.FENCE_LOG.read_text().splitlines()]
    assert len(ev) == 1 and ev[0]["outcome"] == "refused" and ev[0]["seasons"] == ["2223"]
    with pytest.raises(TypeError):  # ya no existe un interruptor booleano para saltar la valla
        wf.run(s, Probe, ["2223"], label="gate3", allow_beyond_fence=True)


def test_reserved_seasons_rejected():
    s = synthetic.generate(n_divisions=1, n_teams=6, seasons=("2324", "2425"), seed=5)
    with pytest.raises(holdout.ReservedDataError):
        wf.run(s, Probe, ["2324"], label="reserved")


def _perturb_future(df, tau, rng):
    d = df.copy()
    fut = d["match_date"] >= tau
    for c in ["fthg", "ftag", "hs", "as_", "hst", "ast", "hc", "ac"]:
        d.loc[fut, c] = rng.permutation(d.loc[fut, c].to_numpy())
    d["total_goals"] = d["fthg"] + d["ftag"]
    d["over25"] = (d["total_goals"] > 2.5).astype(float)
    d.loc[fut, "ou_close_avg_over"] = 1.5
    return d


def test_parallel_equals_serial(syn):
    a, _ = wf.run(syn, Probe, ["0607"], scope="division", n_jobs=1, label="s")
    b, _ = wf.run(syn, Probe, ["0607"], scope="division", n_jobs=2, label="p")
    pd.testing.assert_frame_equal(a.sort_values("match_id").reset_index(drop=True),
                                  b.sort_values("match_id").reset_index(drop=True))


# ---------------------------------------------------------------- features
def test_features_match_bruteforce(syn):
    hl = 7.0
    f = features.build_features(syn, half_life_matches=hl)
    alpha = 1 - 0.5 ** (1 / hl)
    rng = np.random.default_rng(0)
    for i in rng.choice(syn.index, 60, replace=False):
        r = syn.loc[i]
        team = r["home_team"]
        h = syn[((syn.home_team == team) | (syn.away_team == team)) & (syn.match_date < r.info_cutoff_date)]
        h = h.sort_values(["match_date", "match_id"], kind="mergesort")
        if h.empty:
            assert np.isnan(f.loc[i, "feat_h_g_for"]) and f.loc[i, "feat_h_n_prior"] == 0
            continue
        gf = np.where(h.home_team == team, h.fthg, h.ftag)
        exp = pd.Series(gf).ewm(alpha=alpha).mean().iloc[-1]
        assert f.loc[i, "feat_h_g_for"] == pytest.approx(exp, abs=1e-9)
        assert f.loc[i, "feat_h_n_prior"] == len(h)


def test_features_invariant_to_future_outcomes(syn):
    rng = np.random.default_rng(1)
    tau = syn[syn.season_code == "0607"]["pre_odds_capture_date_est"].iloc[100]
    a = features.build_features(syn, 10)
    b = features.build_features(_perturb_future(syn, tau, rng), 10)
    rows = syn["info_cutoff_date"] <= tau
    pd.testing.assert_frame_equal(a[rows], b[rows])
    assert not a[~rows].equals(b[~rows])  # control: la perturbación sí cambia el futuro


def test_features_exclude_same_day():
    d = pd.DataFrame({"match_id": ["a", "b"], "country": ["X", "X"], "div": ["S0", "S0"],
                      "match_date": pd.to_datetime(["2020-01-03", "2020-01-03"]),
                      "info_cutoff_date": pd.to_datetime(["2020-01-03", "2020-01-03"]),
                      "home_team": ["T1", "T2"], "away_team": ["T2", "T1"],
                      "fthg": [3.0, 1.0], "ftag": [0.0, 1.0], "hs": [1.0] * 2, "as_": [1.0] * 2,
                      "hst": [1.0] * 2, "ast": [1.0] * 2, "hc": [1.0] * 2, "ac": [1.0] * 2})
    f = features.build_features(d, 5)
    assert f["feat_h_n_prior"].eq(0).all() and f["feat_h_g_for"].isna().all()


def test_perturb_helper_changes_future_only(syn):
    rng = np.random.default_rng(2)
    tau = pd.Timestamp("2007-01-05")
    p = _perturb_future(syn, tau, rng)
    past = syn["match_date"] < tau
    pd.testing.assert_frame_equal(syn.loc[past, POST[:-1]], p.loc[past, POST[:-1]])

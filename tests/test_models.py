"""Modelos de GATE 2: corrección numérica, anti-filtración y validez metodológica (datos sintéticos)."""
import numpy as np
import pandas as pd
import pytest
from scipy import optimize

from qsports import benchmark, evaluation as ev, features, models, synthetic, walkforward as wf

SEASONS = ["0607", "0708"]


def prep(df, hl=5):
    b = benchmark.market_benchmarks(df)
    df = df.assign(p_A_consensus=b["p_A_consensus"].values, A_consensus_valid=b["A_consensus_valid"].values)
    df["p_C_hist_freq"] = benchmark.historical_frequency(df)
    return pd.concat([df, features.build_features(df, hl)], axis=1)


@pytest.fixture(scope="module")
def syn():
    df = prep(synthetic.generate(n_divisions=2, n_teams=12, seasons=("0506", "0607", "0708"), seed=21))
    rng = np.random.default_rng(0)
    z = np.log(df["true_p_over"] / (1 - df["true_p_over"])) + rng.normal(0, 0.3, len(df))
    df["inp_x"] = 1 / (1 + np.exp(-z))  # entrada pre-partido fija (no se perturba)
    return df


FACTORIES = {
    "M0a": (lambda: models.FreqModel(), "division", 1),
    "M1": (lambda: models.PoissonModel(window_days=365, ridge=4.0), "division", 1),
    "M2": (lambda: models.PoissonModel(half_life_days=240, ridge=4.0, promoted_prior=True), "division", 1),
    "M3": (lambda: models.LogisticFeatureModel(features.feature_columns("GSTC"), ridge=10.0), "pooled", 3),
    "M4cal": (lambda: models.MarketModel([], require_cols=["inp_x"], half_life_days=365), "pooled", 3),
    "M4sport": (lambda: models.MarketModel(["inp_x"], ridge=10.0, require_cols=["inp_x"]), "pooled", 3),
}


def test_poisson_gradient_matches_numerical():
    rng = np.random.default_rng(1)
    n, m = 6, 80
    hi, ai = rng.integers(0, n, m), rng.integers(0, n, m)
    yh, ya, w = rng.poisson(1.4, m).astype(float), rng.poisson(1.1, m).astype(float), rng.uniform(0.2, 1, m)
    th = rng.normal(0, 0.2, 2 + 2 * n)
    args = (hi, ai, yh, ya, w, n, 3.0, np.zeros(n), np.zeros(n))
    err = optimize.check_grad(lambda t: models.PoissonModel.nll(t, *args)[0],
                              lambda t: models.PoissonModel.nll(t, *args)[1], th)
    assert err < 1e-5


def test_poisson_hessian_matches_numerical_and_newton_matches_lbfgs():
    rng = np.random.default_rng(2)
    n, m = 6, 120
    hi, ai = rng.integers(0, n, m), rng.integers(0, n, m)
    keep = hi != ai
    hi, ai = hi[keep], ai[keep]
    yh, ya = rng.poisson(1.4, len(hi)).astype(float), rng.poisson(1.1, len(hi)).astype(float)
    w = rng.uniform(0.2, 1, len(hi))
    args = (hi, ai, yh, ya, w, n, 2.0, np.zeros(n), np.zeros(n))
    th = rng.normal(0, 0.2, 2 + 2 * n)
    H = models.PoissonModel.hessian(th, *args)
    eps = 1e-6
    num = np.column_stack([(models.PoissonModel.nll(th + eps * e, *args)[1] - models.PoissonModel.nll(th - eps * e, *args)[1])
                           / (2 * eps) for e in np.eye(len(th))])
    assert np.allclose(H, num, atol=1e-5)
    x_n, it, g, ok, _ = models.PoissonModel.newton(np.zeros(len(th)), *args)
    r = optimize.minimize(lambda t: models.PoissonModel.nll(t, *args), np.zeros(len(th)), jac=True, method="L-BFGS-B",
                          options={"gtol": 1e-12, "ftol": 1e-15, "maxiter": 5000})
    f_n, g_n = models.PoissonModel.nll(x_n, *args)
    f_l, g_l = models.PoissonModel.nll(r.x, *args)
    assert ok and it < 30
    assert f_n <= f_l + 1e-9 and np.max(np.abs(g_n)) <= np.max(np.abs(g_l)) + 1e-12
    assert np.allclose(x_n, r.x, atol=1e-4)


@pytest.mark.parametrize("name", list(FACTORIES))
def test_model_invariant_to_future(syn, name):
    """Alterar resultados/estadísticas de partidos con fecha >= τ0 no cambia predicciones hechas en τ <= τ0."""
    fac, scope, every = FACTORIES[name]
    tau0 = syn.loc[syn.season_code == "0607", "pre_odds_capture_date_est"].sort_values().iloc[90]
    rng = np.random.default_rng(5)
    d = syn.copy()
    fut = d["match_date"] >= tau0
    for c in ["fthg", "ftag", "hs", "as_", "hst", "ast", "hc", "ac"]:
        d.loc[fut, c] = rng.permutation(d.loc[fut, c].to_numpy())
    d["total_goals"] = d["fthg"] + d["ftag"]
    d["over25"] = (d["total_goals"] > 2.5).astype(float)
    d = prep(d.drop(columns=[c for c in d.columns if c.startswith("feat_")] + ["p_A_consensus", "A_consensus_valid",
                                                                              "p_C_hist_freq"]))
    a, _ = wf.run(syn, fac, SEASONS, scope=scope, refit_every=every, label=name)
    b, _ = wf.run(d, fac, SEASONS, scope=scope, refit_every=every, label=name)
    # propiedad: partidos cuya captura (corte de información) es <= τ0 no cambian. (Con reajuste
    # cada k capturas, un ajuste en τ_k <= τ0 también predice capturas posteriores a τ0, cuyas
    # variables usan legítimamente datos anteriores a su propia captura.)
    cap = syn.set_index("match_id")["pre_odds_capture_date_est"]
    a, b = a[a.match_id.map(cap) <= tau0], b[b.match_id.map(cap) <= tau0]
    ka, kb = a.set_index("match_id"), b.set_index("match_id")
    assert len(ka) > 50
    pd.testing.assert_series_equal(ka["p_over"].sort_index(), kb.loc[ka.index, "p_over"].sort_index())
    # control: la perturbación cambia predicciones posteriores (salvo M0a/M4 si no dependen de ellas)
    if name in ("M1", "M2", "M3"):
        a2, _ = wf.run(syn, fac, SEASONS, scope=scope, refit_every=every, label=name)
        b2, _ = wf.run(d, fac, SEASONS, scope=scope, refit_every=every, label=name)
        later = a2[a2.match_id.map(cap) > tau0].set_index("match_id")["p_over"]
        assert not np.allclose(later.sort_index(), b2.set_index("match_id").loc[later.index, "p_over"].sort_index())


@pytest.mark.parametrize("name", ["M1", "M3", "M4cal", "M4sport"])
def test_batch_independence(syn, name):
    fac, scope, _ = FACTORIES[name]
    tau = syn.loc[syn.season_code == "0708", "pre_odds_capture_date_est"].sort_values().iloc[100]
    div = syn["div"].iloc[0]
    train = syn[(syn.match_date < tau) & ((syn["div"] == div) if scope == "division" else True)]
    rows = wf.prematch_view(syn[(syn.season_code == "0708") & (syn["div"] == div)].head(30))
    m = fac()
    m.fit(train, tau)
    full = m.predict(rows)
    single = np.array([m.predict(rows.iloc[[i]])[0] for i in range(len(rows))])
    assert np.allclose(full, single, rtol=0, atol=1e-12)


def test_poisson_recovers_signal_and_converges(syn):
    p, logs = wf.run(syn, FACTORIES["M2"][0], SEASONS, scope="division", label="M2")
    m = syn[["match_id", "true_p_over", "over25"]].merge(p, on="match_id")
    assert logs["converged"].all()
    assert np.corrcoef(m["true_p_over"], m["p_over"])[0, 1] > 0.5
    f, _ = wf.run(syn, FACTORIES["M0a"][0], SEASONS, scope="division", label="M0a")
    mf = m.merge(f.rename(columns={"p_over": "pf"})[["match_id", "pf"]], on="match_id")
    assert ev.log_loss(mf.over25, mf.p_over).mean() < ev.log_loss(mf.over25, mf.pf).mean()


@pytest.mark.parametrize("sees,expect_incremental", [(True, False), (False, True)])
def test_m4_sport_vs_cal_detects_incremental_information_only_when_present(sees, expect_incremental):
    """Validez metodológica (exigencia 4): con un mercado que ya incorpora la 'forma', M4-sport no
    supera a M4-cal; si el mercado la ignora, la comparación detecta el aporte deportivo."""
    df = prep(synthetic.generate(n_divisions=3, n_teams=16, market_sees_form=sees, form_sd=0.3, seed=11))
    cols = features.feature_columns("GS")
    p3, _ = wf.run(df, lambda: models.LogisticFeatureModel(cols, ridge=10), ["0607", "0708", "0809", "0910", "1011",
                                                                            "1112", "1213"], scope="pooled",
                   refit_every=6, label="m3")
    df = df.merge(p3[["match_id", "p_over"]].rename(columns={"p_over": "inp_m3"}), on="match_id", how="left")
    s = ["0809", "0910", "1011", "1112", "1213"]
    pc, _ = wf.run(df, lambda: models.MarketModel([], require_cols=["inp_m3"]), s, scope="pooled", refit_every=6, label="c")
    ps, _ = wf.run(df, lambda: models.MarketModel(["inp_m3"], ridge=10, require_cols=["inp_m3"]), s, scope="pooled",
                   refit_every=6, label="s")
    m = (df[["match_id", "match_date", "over25"]].merge(pc[["match_id", "p_over"]].rename(columns={"p_over": "c"}))
         .merge(ps[["match_id", "p_over"]].rename(columns={"p_over": "s"})).dropna())
    r = ev.compare(m.over25, m.s, m.c, m.match_date, delta=0.001, n_boot=2000)
    assert (r["category"] in ("S-R", "S-NR")) is expect_incremental, r

"""GATE 4: auditoría matemática y de implementación de M4-cal (candidato primario único).

M4-cal: logit p = a + b·logit p_A, estimado por máxima verosimilitud bernoulli ponderada con pesos
w_i = 2^(−edad_i / 730 días), sin penalización sobre (a, b), con las filas de entrenamiento que tienen p_A, resultado
e `inp_m2` disponibles (la columna solo define el subconjunto; su valor no interviene).
"""
import math

import numpy as np
import pandas as pd
import pytest
from scipy import optimize

from qsports import models, paths, process

RNG = np.random.default_rng(2026)


def _objective(b, X, y, w, pen, lam):
    eta = X @ b
    return np.sum(w * (np.logaddexp(0, eta) - y * eta)) + 0.5 * lam * np.sum(pen * b * b)


def _gradient(b, X, y, w, pen, lam):
    mu = 1 / (1 + np.exp(-(X @ b)))
    return X.T @ (w * (mu - y)) + lam * pen * b


def _irls(X, y, w, iters=50):
    """Solver independiente (Newton/IRLS) para la regresión logística ponderada sin penalización."""
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        mu = 1 / (1 + np.exp(-(X @ b)))
        H = (X * (w * mu * (1 - mu))[:, None]).T @ X
        step = np.linalg.solve(H, X.T @ (w * (y - mu)))
        b = b + step
        if np.max(np.abs(step)) < 1e-14:
            break
    return b


def _cal_data(n, a=0.05, b=1.2, seed=0):
    rng = np.random.default_rng(seed)
    pA = rng.uniform(0.25, 0.75, n)
    zA = np.log(pA / (1 - pA))
    p = 1 / (1 + np.exp(-(a + b * zA)))
    y = (rng.uniform(size=n) < p).astype(float)
    return pA, zA, y


def _frame(pA, y, tau, ages, inp=None):
    return pd.DataFrame({"p_A_consensus": pA, "over25": y, "inp_m2": 0.5 if inp is None else inp,
                         "match_date": tau - pd.to_timedelta(ages, unit="D")})


M4CAL = dict(sport_cols=[], ridge=100.0, half_life_days=730, require_cols=["inp_m2"], market_col="p_A_consensus")


def test_logistic_objective_gradient_matches_numerical():
    n = 400
    X = np.column_stack([np.ones(n), RNG.normal(0, 0.6, n)])
    y = (RNG.uniform(size=n) < 0.5).astype(float)
    w = RNG.uniform(0.1, 1, n)
    for b in (np.array([0.1, 0.9]), np.array([-0.3, 1.4])):
        err = optimize.check_grad(_objective, _gradient, b, X, y, w, np.zeros(2), 100.0)
        assert err < 1e-5


def test_fit_logistic_matches_independent_irls_solver():
    pA, zA, y = _cal_data(20_000, seed=1)
    X = np.column_stack([np.ones(len(y)), zA])
    w = np.exp(-math.log(2) * RNG.uniform(0, 3000, len(y)) / 730)
    b_impl, r = models.fit_logistic(X, y, w, np.zeros(2), 100.0, x0=np.r_[0.0, 1.0])
    b_ref = _irls(X, y, w)
    assert r.success
    assert np.allclose(b_impl, b_ref, atol=2e-6), (b_impl, b_ref)
    f_impl, f_ref = _objective(b_impl, X, y, w, np.zeros(2), 0), _objective(b_ref, X, y, w, np.zeros(2), 0)
    assert f_impl - f_ref < 1e-7 * abs(f_ref)


def test_m4cal_recovers_known_calibration():
    pA, _, y = _cal_data(200_000, a=0.05, b=1.2, seed=2)
    tau = pd.Timestamp("2020-01-01")
    m = models.MarketModel(**M4CAL)
    info = m.fit(_frame(pA, y, tau, np.zeros(len(y))), tau)
    assert info["converged"]
    assert m.beta[0] == pytest.approx(0.05, abs=0.02) and m.beta[1] == pytest.approx(1.2, abs=0.03)


def test_exponential_weights_halve_every_730_days():
    """Dos copias de una observación con 731 días de antigüedad pesan lo mismo que una con 1 día: 2·2^(−731/730) =
    2^(−1/730). El ajuste debe coincidir (a la tolerancia del optimizador)."""
    tau = pd.Timestamp("2020-01-01")
    pA, _, y = _cal_data(3000, seed=3)
    ages = RNG.integers(2, 2000, len(y))
    extra_p, extra_y = np.array([0.7, 0.35]), np.array([1.0, 0.0])
    one = _frame(np.r_[pA, extra_p], np.r_[y, extra_y], tau, np.r_[ages, [1, 1]])
    two = _frame(np.r_[pA, extra_p, extra_p], np.r_[y, extra_y, extra_y], tau, np.r_[ages, [731, 731, 731, 731]])
    m1, m2 = models.MarketModel(**M4CAL), models.MarketModel(**M4CAL)
    m1.fit(one, tau)
    m2.fit(two, tau)
    assert np.allclose(m1.beta, m2.beta, atol=1e-5)
    m3 = models.MarketModel(**M4CAL)  # control: misma antigüedad sin duplicar -> distinto
    m3.fit(_frame(np.r_[pA, extra_p], np.r_[y, extra_y], tau, np.r_[ages, [731, 731]]), tau)
    assert not np.allclose(m1.beta, m3.beta, atol=1e-5)


def test_inp_m2_values_irrelevant_only_availability_matters():
    tau = pd.Timestamp("2020-01-01")
    pA, _, y = _cal_data(5000, seed=4)
    ages = RNG.integers(1, 3000, len(y))
    rows = pd.DataFrame({"p_A_consensus": RNG.uniform(0.3, 0.7, 50), "inp_m2": RNG.uniform(0, 1, 50)})
    inp = RNG.uniform(0.2, 0.8, len(y))
    base = models.MarketModel(**M4CAL)
    base.fit(_frame(pA, y, tau, ages, inp), tau)
    other = models.MarketModel(**M4CAL)  # otros valores, mismo patrón de disponibilidad
    other.fit(_frame(pA, y, tau, ages, RNG.uniform(0.2, 0.8, len(y))), tau)
    assert np.array_equal(base.predict(rows), other.predict(rows))
    assert np.array_equal(base.predict(rows), base.predict(rows.assign(inp_m2=np.nan)))  # al predecir no se usa
    masked = inp.copy()
    masked[:1500] = np.nan  # otro patrón de disponibilidad -> otra muestra de entrenamiento
    m3 = models.MarketModel(**M4CAL)
    m3.fit(_frame(pA, y, tau, ages, masked), tau)
    assert not np.array_equal(base.predict(rows), m3.predict(rows))


def test_ridge_inert_for_m4cal():
    """Sin columnas deportivas, ningún coeficiente está penalizado: el argumento ridge congelado (100) es inerte."""
    tau = pd.Timestamp("2020-01-01")
    pA, _, y = _cal_data(4000, seed=5)
    f = _frame(pA, y, tau, RNG.integers(1, 2000, len(y)))
    a, b = models.MarketModel(**{**M4CAL, "ridge": 1.0}), models.MarketModel(**{**M4CAL, "ridge": 1e6})
    a.fit(f, tau)
    b.fit(f, tau)
    assert np.array_equal(a.beta, b.beta)


def test_insufficient_training_gives_nan_and_prediction_formula():
    tau = pd.Timestamp("2020-01-01")
    pA, _, y = _cal_data(150, seed=6)
    m = models.MarketModel(**M4CAL)
    assert m.fit(_frame(pA, y, tau, np.ones(150)), tau)["message"] == "insuficiente"
    assert np.isnan(m.predict(pd.DataFrame({"p_A_consensus": [0.5]}))).all()
    pA, _, y = _cal_data(5000, seed=7)
    m.fit(_frame(pA, y, tau, np.ones(5000)), tau)
    p = np.array([0.3, 0.5, 0.8])
    expected = 1 / (1 + np.exp(-(m.beta[0] + m.beta[1] * np.log(p / (1 - p)))))
    assert np.allclose(m.predict(pd.DataFrame({"p_A_consensus": p})), expected, atol=1e-15)


def test_clipping_inactive_on_development_data():
    """El recorte de p_A a [1e-6, 1−1e-6] no actúa en ninguna fila del desarrollo."""
    if not (paths.PROCESSED_DEV / "matches.parquet").exists():
        pytest.skip("Requiere los datos de desarrollo")
    b = process.load_dev_benchmarks()["p_A_consensus"].dropna()
    assert b.min() > 1e-6 and b.max() < 1 - 1e-6

"""Evaluador: propiedades conocidas verificadas con datos sintéticos."""
import math

import numpy as np
import pandas as pd
import pytest

from qsports import evaluation as ev

RNG = np.random.default_rng(7)


def test_losses_reference_values():
    assert ev.log_loss([1], [0.5])[0] == pytest.approx(math.log(2))
    assert ev.brier([0], [0.5])[0] == pytest.approx(0.25)
    assert ev.log_loss([1], [1.0])[0] < 1e-9  # recortado, finito


def test_calibration_recovers_known_slope():
    p = RNG.uniform(0.2, 0.8, 200_000)
    y = (RNG.uniform(size=p.size) < p).astype(float)
    c = ev.calibration(y, p)
    assert c["slope"] == pytest.approx(1.0, abs=0.03)
    assert c["intercept_in_the_large"] == pytest.approx(0.0, abs=0.02)
    # pronóstico demasiado extremo: logit duplicado -> pendiente ~0,5
    z = np.log(p / (1 - p))
    p_over = 1 / (1 + np.exp(-2 * z))
    assert ev.calibration(y, p_over)["slope"] == pytest.approx(0.5, abs=0.03)


def test_murphy_identity_exact_for_discrete_forecasts():
    p = RNG.choice(np.linspace(0.05, 0.95, 10), 5000)
    y = (RNG.uniform(size=p.size) < p).astype(float)
    m = ev.murphy_decomposition(y, p)
    assert m["brier"] == pytest.approx(m["reliability"] - m["resolution"] + m["uncertainty"], abs=1e-12)


def test_ece_small_when_calibrated_large_when_not():
    p = RNG.uniform(0.3, 0.7, 100_000)
    y = (RNG.uniform(size=p.size) < p).astype(float)
    assert ev.ece(y, p) < 0.01
    assert ev.ece(y, np.clip(p + 0.1, 0, 1)) > 0.08


def test_auc_matches_bruteforce():
    p = RNG.uniform(size=300)
    y = (RNG.uniform(size=300) < p).astype(float)
    pos, neg = p[y == 1], p[y == 0]
    brute = np.mean([(a > b) + 0.5 * (a == b) for a in pos for b in neg])
    assert ev.auc(y, p) == pytest.approx(brute, abs=1e-12)


def test_week_ids_monday_to_sunday():
    w = ev.week_ids(pd.to_datetime(["2023-10-02", "2023-10-08", "2023-10-09"]))
    assert w[0] == w[1] != w[2]


def test_block_bootstrap_coverage_iid():
    hits = 0
    reps = 150
    for r in range(reps):
        rng = np.random.default_rng(r)
        d = rng.normal(0.3, 1.0, 2000)
        weeks = np.repeat(np.arange(100), 20)
        b = ev.block_bootstrap_mean(d, weeks, block=4, n_boot=500, seed=r)
        hits += b["lo"] <= 0.3 <= b["hi"]
    assert 0.88 <= hits / reps <= 0.99


def test_block_bootstrap_wider_under_weekly_shocks():
    rng = np.random.default_rng(1)
    weeks = np.repeat(np.arange(200), 30)
    shock = rng.normal(0, 1.0, 200)[weeks]
    d = shock + rng.normal(0, 1.0, weeks.size)
    b = ev.block_bootstrap_mean(d, weeks, n_boot=2000)
    naive_half = 1.96 * d.std(ddof=1) / math.sqrt(d.size)
    assert (b["hi"] - b["lo"]) / 2 > 2 * naive_half
    assert ev.design_effect(d, weeks) > 5


def test_diebold_mariano():
    weeks = np.repeat(np.arange(100), 10)
    assert ev.diebold_mariano(np.zeros(1000), weeks)["p_value"] == 1.0
    rng = np.random.default_rng(3)
    assert ev.diebold_mariano(rng.normal(-0.2, 1, 1000), weeks)["p_value"] < 0.01
    assert ev.diebold_mariano(rng.normal(0.0, 1, 1000), weeks)["p_value"] > 0.001


@pytest.mark.parametrize("lo,hi,cat", [
    (-0.005, -0.002, "S-R"), (-0.005, -0.001, "S-NR"), (-0.003, -0.0005, "S-NR"),
    (-0.0008, 0.0008, "EQ"), (-0.0008, 0.0, "EQ"), (-0.001, 0.0005, "INC"), (-0.003, 0.003, "INC"),
    (-0.0005, 0.001, "INC"), (0.0002, 0.0008, "I-NR"), (0.0005, 0.001, "I-NR"), (0.0011, 0.003, "I-R"),
])
def test_decision_category_borders(lo, hi, cat):
    assert ev.decision_category(lo, hi, 0.001) == cat


def test_decision_partition_is_exclusive_and_exhaustive():
    """Comprueba con predicados independientes que cada (L, U) cae en exactamente una categoría."""
    delta = 0.001
    preds = {
        "S-R": lambda L, U: U < -delta,
        "S-NR": lambda L, U: -delta <= U < 0,
        "EQ": lambda L, U: L <= 0 <= U and L > -delta and U < delta,
        "INC": lambda L, U: L <= 0 <= U and (L <= -delta or U >= delta),
        "I-NR": lambda L, U: 0 < L <= delta,
        "I-R": lambda L, U: L > delta,
    }
    rng = np.random.default_rng(0)
    pts = rng.uniform(-0.004, 0.004, size=(20000, 2))
    grid = np.array([-0.002, -0.001, -0.0005, 0.0, 0.0005, 0.001, 0.002])
    pts = np.vstack([pts, np.array([(a, b) for a in grid for b in grid])])
    for a, b in pts:
        L, U = min(a, b), max(a, b)
        hits = [k for k, f in preds.items() if f(L, U)]
        assert len(hits) == 1, (L, U, hits)
        assert ev.decision_category(L, U, delta) == hits[0]


def test_mde_formula():
    assert ev.mde(0.114, 15000, 1.23) == pytest.approx(0.00290, abs=2e-5)


def test_compare_detects_better_model():
    n = 20000
    p_true = RNG.uniform(0.3, 0.7, n)
    y = (RNG.uniform(size=n) < p_true).astype(float)
    dates = pd.date_range("2010-01-01", periods=n, freq="6h")
    res = ev.compare(y, p_true, np.full(n, 0.5), dates, delta=0.001, n_boot=1000)
    assert res["delta_logloss"]["hi"] < 0 and res["category"] in ("S-R", "S-NR")

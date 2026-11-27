"""GATE 2.1: validación de entradas, bootstrap por semanas calendario, dependencia serial sintética y
potencia de superioridad frente a equivalencia."""
import math

import numpy as np
import pandas as pd
import pytest

from qsports import evaluation as ev
from qsports import validation as val
from qsports.validation import InputValidationError


# ---------------------------------------------------------------- exigencia 3: validación
@pytest.mark.parametrize("p", [[0.5, 1.2], [-0.1, 0.5], [0.5, np.inf], [0.5, -np.inf], [0.5, np.nan]])
def test_probabilities_rejected(p):
    with pytest.raises(InputValidationError):
        ev.log_loss([1, 0], p)
    with pytest.raises(InputValidationError):
        ev.brier([1, 0], p)


@pytest.mark.parametrize("y", [[1, 2], [0.5, 1], [np.nan, 1], [np.inf, 0]])
def test_outcomes_must_be_binary(y):
    with pytest.raises(InputValidationError):
        ev.log_loss(y, [0.5, 0.5])


def test_dimensions_and_empty():
    with pytest.raises(InputValidationError):
        ev.log_loss([1, 0, 1], [0.5, 0.5])
    with pytest.raises(InputValidationError):
        ev.log_loss([], [])
    with pytest.raises(InputValidationError):
        ev.compare([1, 0], [0.5, 0.5], [0.5, 0.5], ["2020-01-01"], delta=0.001, n_boot=10)


def test_log_loss_exact_and_infinite_loss_rejected():
    assert ev.log_loss([1, 0], [1.0, 0.0]).tolist() == [0.0, 0.0]  # sin recorte: exacta
    assert ev.log_loss([1], [0.25])[0] == pytest.approx(math.log(4))
    with pytest.raises(InputValidationError):
        ev.log_loss([0], [1.0])  # pérdida infinita: se rechaza, no se recorta
    with pytest.raises(InputValidationError):
        ev.calibration([0, 1], [0.0, 0.5])  # logit indefinido


def test_unique_ids_and_one_to_one_merge():
    a = pd.DataFrame({"match_id": ["x", "y", "y"], "p": [0.1, 0.2, 0.3]})
    b = pd.DataFrame({"match_id": ["x", "y"], "q": [0.5, 0.6]})
    with pytest.raises(InputValidationError):
        val.unique_ids(a, context="t")
    with pytest.raises(InputValidationError):
        val.merge_one_to_one(b, a, context="t")
    m = val.merge_one_to_one(b, b.rename(columns={"q": "r"}), context="t")
    assert len(m) == 2


def test_coverage_and_full_coverage_requirement():
    uni = pd.DataFrame({"match_id": ["a", "b", "c"]})
    ok = pd.DataFrame({"match_id": ["a", "b", "c", "z"], "p_over": [0.4, 0.5, 0.6, 0.7]})
    cov = val.require_full_coverage(ok, uni, "ok")
    assert cov["missing"] == 0 and cov["extra"] == 1 and cov["coverage"] == 1.0
    with pytest.raises(InputValidationError):
        val.require_full_coverage(ok[ok.match_id != "b"], uni, "falta")
    with pytest.raises(InputValidationError):
        val.require_full_coverage(ok.assign(p_over=[0.4, np.nan, 0.6, 0.7]), uni, "nan")
    with pytest.raises(InputValidationError):
        val.require_full_coverage(pd.concat([ok, ok.iloc[[0]]]), uni, "duplicado")


# ---------------------------------------------------------------- exigencia 2: semanas calendario
def test_week_ids_are_consecutive_calendar_weeks():
    w = ev.week_ids(pd.to_datetime(["2023-10-02", "2023-10-08", "2023-10-09", "2023-10-30"]))
    assert w[0] == w[1] and w[2] == w[0] + 1 and w[3] == w[0] + 4


def test_calendar_series_includes_empty_weeks_active_does_not():
    weeks = np.array([0, 0, 1, 5, 5, 6])  # semanas 2-4 sin partidos (pausa)
    d = np.array([1.0, 1.0, 2.0, 3.0, 3.0, 4.0])
    S, N = ev._weekly_totals(d, weeks, "calendar")
    assert S.tolist() == [2.0, 2.0, 0.0, 0.0, 0.0, 6.0, 4.0] and N.tolist() == [2, 1, 0, 0, 0, 2, 1]
    S2, N2 = ev._weekly_totals(d, weeks, "active")
    assert len(S2) == 4


def test_calendar_blocks_do_not_join_weeks_across_a_long_pause():
    """Con bloques de 2 semanas calendario, ningún bloque contiene la última semana antes de una pausa de
    10 semanas y la primera después; con semanas activas sí. Se comprueba vía la varianza bootstrap en un
    caso construido: valores alternos +1/−1 antes y después de la pausa."""
    weeks = np.r_[np.arange(0, 6), np.arange(16, 22)]
    d = np.r_[np.ones(6), -np.ones(6)]
    a = ev.block_bootstrap_mean(d, weeks, block=2, n_boot=4000, seed=1, week_mode="active")
    c = ev.block_bootstrap_mean(d, weeks, block=2, n_boot=4000, seed=1, week_mode="calendar")
    assert a["weeks"] == 12 and c["weeks"] == 22 and c["weeks_with_matches"] == 12
    assert c["mean"] == pytest.approx(0.0) and a["mean"] == pytest.approx(0.0)
    assert c["block_weeks"] == 2 and c["week_mode"] == "calendar"


def test_bootstrap_rejects_replicates_without_observations():
    weeks = np.r_[0, 200]  # dos semanas aisladas: muchas réplicas vacías con bloques de 1
    with pytest.raises(InputValidationError):
        ev.block_bootstrap_mean(np.array([1.0, 2.0]), weeks, block=1, n_boot=2000, week_mode="calendar")


def _season_weeks(n_seasons=6, active=38, pause=14):
    return np.concatenate([np.arange(active) + s * (active + pause) for s in range(n_seasons)])


def _ar1(n, phi, sd, rng):
    u = np.empty(n)
    u[0] = rng.normal(0, sd / math.sqrt(1 - phi ** 2))
    for i in range(1, n):
        u[i] = phi * u[i - 1] + rng.normal(0, sd)
    return u


def test_serial_dependence_block_bootstrap_covers_iid_week_bootstrap_does_not():
    """Dependencia serial sintética: shock semanal AR(1) (φ = 0,7) común a todos los partidos de la semana,
    con pausas entre temporadas. Bloques de 1 semana (independencia entre semanas) infra-cubren; bloques de
    8 semanas calendario se acercan al 95 %."""
    aw = _season_weeks()
    reps, hits1, hits8 = 200, 0, 0
    for r in range(reps):
        rng = np.random.default_rng(1000 + r)
        u = _ar1(len(aw), 0.7, 0.5, rng)
        weeks = np.repeat(aw, 20)
        d = np.repeat(u, 20) + rng.normal(0, 1.0, weeks.size)
        b1 = ev.block_bootstrap_mean(d, weeks, block=1, n_boot=400, seed=r)
        b8 = ev.block_bootstrap_mean(d, weeks, block=8, n_boot=400, seed=r)
        hits1 += b1["lo"] <= 0 <= b1["hi"]
        hits8 += b8["lo"] <= 0 <= b8["hi"]
    c1, c8 = hits1 / reps, hits8 / reps
    assert c1 < 0.80, c1
    assert c8 > 0.85 and c8 > c1 + 0.15, (c1, c8)


def test_serial_dependence_dm_hac_less_oversized_than_no_lag():
    aw = _season_weeks()
    rej0 = rejh = 0
    reps = 200
    for r in range(reps):
        rng = np.random.default_rng(5000 + r)
        u = _ar1(len(aw), 0.7, 0.5, rng)
        weeks = np.repeat(aw, 20)
        d = np.repeat(u, 20) + rng.normal(0, 1.0, weeks.size)
        rej0 += ev.diebold_mariano(d, weeks, lag=0)["p_value"] < 0.05
        rejh += ev.diebold_mariano(d, weeks)["p_value"] < 0.05
    assert rej0 / reps > 0.20 and rejh / reps < rej0 / reps - 0.10, (rej0, rejh)


def test_no_dependence_block_choice_irrelevant_for_coverage():
    aw = _season_weeks(4)
    hits = {2: 0, 12: 0}
    reps = 150
    for r in range(reps):
        rng = np.random.default_rng(9000 + r)
        weeks = np.repeat(aw, 15)
        d = rng.normal(0.0, 1.0, weeks.size)
        for L in hits:
            b = ev.block_bootstrap_mean(d, weeks, block=L, n_boot=400, seed=r)
            hits[L] += b["lo"] <= 0 <= b["hi"]
    for L, h in hits.items():
        assert 0.86 <= h / reps <= 0.99, (L, h / reps)


# ---------------------------------------------------------------- potencia: superioridad vs equivalencia
@pytest.mark.parametrize("theta", [0.0, -0.0006, 0.0004, -0.0015])
def test_prob_categories_match_monte_carlo(theta):
    se, delta, z = 0.0003, 0.001, 1.959963984540054
    p = ev.prob_categories(theta, se, delta)
    assert sum(v for k, v in p.items() if k in ev.CATEGORIES) == pytest.approx(1.0, abs=1e-12)
    rng = np.random.default_rng(3)
    est = rng.normal(theta, se, 200_000)
    cats = np.array([ev.decision_category(e - z * se, e + z * se, delta) for e in est[:20_000]])
    for k in ev.CATEGORIES:
        assert p[k] == pytest.approx(np.mean(cats == k), abs=0.012), k
    within = np.mean((est - z * se > -delta) & (est + z * se < delta))
    assert p["CI_within_margin"] == pytest.approx(within, abs=0.005)


def test_power_profile_distinguishes_superiority_and_equivalence():
    pp = ev.power_profile(se=0.0003, delta=0.001)
    assert pp["mde_superiority_vs_zero"] == pytest.approx(2.8016 * 0.0003, rel=1e-3)
    assert pp["mde_superiority_relevant"] == pytest.approx(0.001 + 2.8016 * 0.0003, rel=1e-3)
    assert pp["p_equivalence_at_zero"] > 0.8 and 0 < pp["max_theta_equivalence"] < 0.001
    weak = ev.power_profile(se=0.0008, delta=0.001)  # potencia de superioridad útil, equivalencia imposible
    assert weak["p_equivalence_at_zero"] < 0.05 and weak["max_theta_equivalence"] is None
    se_need = pp["se_needed_equivalence"]
    assert ev.power_profile(se_need, 0.001)["p_equivalence_at_zero"] == pytest.approx(0.8, abs=1e-6)


def test_weekly_autocorrelation_detects_persistence():
    aw = _season_weeks()
    rng = np.random.default_rng(77)
    weeks = np.repeat(aw, 20)
    dep = np.repeat(_ar1(len(aw), 0.7, 0.5, rng), 20) + rng.normal(0, 1.0, weeks.size)
    ind = rng.normal(0, 1.0, weeks.size)
    a_dep = ev.weekly_autocorrelation(dep, weeks, 4, "active")
    a_ind = ev.weekly_autocorrelation(ind, weeks, 4, "active")
    assert a_dep[0] > 0.4 and abs(a_ind[0]) < 0.15

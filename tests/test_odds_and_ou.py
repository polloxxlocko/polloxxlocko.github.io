"""Matemática de cuotas y del mercado O/U 2,5: casos verificables independientemente."""
import math

import numpy as np
import pytest

from qsports import odds, ou


@pytest.mark.parametrize("q,p", [(2.0, 0.5), (1.5, 2 / 3), (3.5, 0.285714)])
def test_implied_probability(q, p):
    assert odds.implied_probability(q) == pytest.approx(p, abs=1e-6)


@pytest.mark.parametrize("p,q,ev", [(0.62, 1.80, 0.116), (0.60, 1.80, 0.08), (0.55, 1.80, -0.01), (0.60, 3.00, 0.80)])
def test_expected_value_reference_cases(p, q, ev):
    # Casos obligatorios del encargo (EV = p*Q - 1, sin re-descontar margen)
    assert odds.expected_value(p, q) == pytest.approx(ev, abs=1e-12)


def test_overround_requires_complete_market():
    with pytest.raises(ValueError):
        odds.overround([1.9])
    # 1X2 completo: 2.10/3.40/3.60
    ov = odds.overround([2.10], [3.40], [3.60])
    assert ov[0] == pytest.approx(1 / 2.1 + 1 / 3.4 + 1 / 3.6 - 1)


def test_proportional_sums_to_one_and_ratio_preserved():
    o, u = np.array([1.80, 2.50]), np.array([2.05, 1.55])
    po, pu = odds.normalize_proportional(o, u)
    assert np.allclose(po + pu, 1)
    assert po[0] / pu[0] == pytest.approx((1 / 1.80) / (1 / 2.05))


def test_power_method_properties():
    o, u = np.array([1.80, 1.91, 1.4]), np.array([2.05, 1.91, 3.0])
    po, pu = odds.normalize_power(o, u)
    assert np.allclose(po + pu, 1, atol=1e-9)
    assert po[1] == pytest.approx(0.5, abs=1e-9)  # precios iguales -> 0,5
    # sin margen, potencia == proporcional
    po0, _ = odds.normalize_power(np.array([2.0]), np.array([2.0]))
    assert po0[0] == pytest.approx(0.5)
    # el método de potencia asigna menos probabilidad que el proporcional al resultado más improbable
    pp, _ = odds.normalize_proportional(np.array([3.0]), np.array([1.4]))
    pw, _ = odds.normalize_power(np.array([3.0]), np.array([1.4]))
    assert pw[0] < pp[0]


def test_clv_and_validity():
    assert odds.closing_line_value(2.10, 2.00) == pytest.approx(0.05)
    assert list(odds.valid_odds([1.0, 1.01, np.nan, 3.5])) == [False, True, False, True]


def test_logit_roundtrip():
    p = np.array([0.1, 0.5, 0.9])
    assert np.allclose(odds.inv_logit(odds.logit(p)), p)


def test_settlement_over25():
    assert list(ou.settle_over25([2, 1, 0, 3], [1, 1, 0, 0])) == [1.0, 0.0, 0.0, 1.0]
    assert np.isnan(ou.settle_over25([np.nan], [1])[0])


def test_poisson_reference_and_over_formula():
    assert ou.poisson_pmf(0, 1.0) == pytest.approx(0.367879, abs=1e-6)
    for lam in (0.5, 1.0, 2.6, 4.0):
        exact = ou.p_over25_poisson(lam)
        under = sum(ou.poisson_pmf(k, lam) for k in range(3))
        assert exact == pytest.approx(1 - under, abs=1e-15)
        # suma truncada k=3..60: masa omitida < 1e-12 (tolerancia documentada)
        trunc = sum(ou.poisson_pmf(k, lam) for k in range(3, 61))
        assert abs(exact - trunc) < 1e-12
        assert 0 < exact < 1

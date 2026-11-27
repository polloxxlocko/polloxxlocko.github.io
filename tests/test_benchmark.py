"""Benchmarks de mercado (A/B/A*) y elemental (C)."""
import numpy as np
import pandas as pd
import pytest

from qsports import benchmark


def _df(**cols):
    n = len(next(iter(cols.values())))
    base = {"match_id": [f"m{i}" for i in range(n)], "match_date": pd.to_datetime(["2023-01-07"] * n)}
    base.update(cols)
    return pd.DataFrame(base)


def test_pair_fair_validity_reasons():
    d = _df(ou_pre_avg_over=[1.9, np.nan, 1.0, 1.2, 1.95], ou_pre_avg_under=[1.95, 1.9, 1.9, 1.2, 1.95])
    r = benchmark.pair_fair(d, "ou_pre_avg")
    assert list(r.invalid_reason) == ["", "missing", "odds<1.01", "overround_out_of_range", ""]
    assert r.p_over.iloc[0] == pytest.approx((1 / 1.9) / (1 / 1.9 + 1 / 1.95))
    assert r.p_over.iloc[4] == pytest.approx(0.5)
    assert r.valid.sum() == 2


def test_pinnacle_masked_only_after_rule_date_and_rows_kept():
    d = pd.DataFrame({
        "match_id": ["a", "b"], "match_date": pd.to_datetime(["2025-07-22", "2025-07-23"]),
        "ou_pre_pin_over": [1.9, 1.9], "ou_pre_pin_under": [1.95, 1.95],
        "ou_pre_b365_over": [1.9, 1.9], "ou_pre_b365_under": [1.9, 1.9],
        "ou_pre_avg_over": [1.9, 1.9], "ou_pre_avg_under": [1.9, 1.9],
        "ou_close_avg_over": [1.9, 1.9], "ou_close_avg_under": [1.9, 1.9]})
    b = benchmark.market_benchmarks(d)
    assert len(b) == 2  # ningún partido eliminado
    assert list(b.A_pin_valid) == [True, False]
    assert list(b.A_b365_valid) == [True, True] and list(b.A_consensus_valid) == [True, True]
    assert b.Astar_n_books.tolist() == [2, 1]


def test_max_pair_never_used_as_fair_probability():
    d = _df(ou_pre_avg_over=[1.9], ou_pre_avg_under=[1.9], ou_pre_max_over=[2.1], ou_pre_max_under=[2.05],
            ou_close_avg_over=[1.9], ou_close_avg_under=[1.9])
    b = benchmark.market_benchmarks(d)
    assert not [c for c in b.columns if c.startswith("p_") and "max" in c]
    assert b.best_price_pre_over.iloc[0] == 2.1


def test_common_sample_requires_all_valid():
    b = pd.DataFrame({"A_consensus_valid": [True, True, False], "A_b365_valid": [True, False, True]})
    assert list(benchmark.common_sample(b, ["A_consensus", "A_b365"])) == [True, False, False]


def test_historical_frequency_is_point_in_time():
    d = pd.DataFrame({
        "div": ["E0"] * 5 + ["D1"],
        "match_date": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-03", "2020-01-10", "2020-01-02"]),
        "over25": [1.0, 0.0, 1.0, 1.0, np.nan, 1.0],
    })
    d["info_cutoff_date"] = d["match_date"]  # usa solo fechas estrictamente anteriores
    p = benchmark.historical_frequency(d)
    assert p.iloc[0] == pytest.approx(0.5)            # sin historia: (0+1)/(0+2)
    assert p.iloc[1] == pytest.approx((1 + 1) / (1 + 2))
    assert p.iloc[2] == p.iloc[3] == pytest.approx((1 + 1) / (2 + 2))  # mismo día excluido
    assert p.iloc[4] == pytest.approx((3 + 1) / (4 + 2))
    assert p.iloc[5] == pytest.approx(0.5)            # división separada

"""Arquitectura point-in-time: regla de captura, corte de información, zona horaria."""
import numpy as np
import pandas as pd
import pytest

from qsports import temporal

WEEK = pd.date_range("2023-10-02", "2023-10-08")  # lunes..domingo
EXPECTED_CAPTURE = ["2023-09-29", "2023-10-03", "2023-10-03", "2023-10-03", "2023-10-06", "2023-10-06", "2023-10-06"]
EXPECTED_RULE = ["weekend_friday", "midweek_tuesday", "midweek_tuesday", "midweek_tuesday",
                 "weekend_friday", "weekend_friday", "weekend_friday"]


def _frame(dates, times):
    return pd.DataFrame({"match_date": pd.to_datetime(dates), "kickoff_time_uk": pd.Series(times, dtype="string"),
                         "season_code": "2324"})


def test_capture_date_rule_for_each_weekday():
    cap, rule = temporal.capture_date_for(pd.Series(WEEK))
    assert [d.strftime("%Y-%m-%d") for d in cap] == EXPECTED_CAPTURE
    assert list(rule) == EXPECTED_RULE


def test_cutoff_never_after_match_and_same_day_excluded():
    rng = np.random.default_rng(0)
    dates = pd.Series(pd.to_datetime("2005-08-01") + pd.to_timedelta(rng.integers(0, 6000, 5000), unit="D"))
    cap, _ = temporal.capture_date_for(dates)
    assert (cap <= dates).all()
    assert ((dates - cap).dt.days <= 3).all()
    # un resultado del mismo día de captura nunca es utilizable
    assert not temporal.history_mask(pd.Series([cap.iloc[0]]), cap.iloc[0]).iloc[0]
    assert temporal.history_mask(pd.Series([cap.iloc[0] - pd.Timedelta(days=1)]), cap.iloc[0]).iloc[0]


@pytest.mark.parametrize("date,time,amb", [
    ("2023-10-06", "15:00", True),   # viernes antes del límite 17:00
    ("2023-10-06", "19:45", False),
    ("2023-10-03", "12:30", True),   # martes antes del límite 13:00
    ("2023-10-03", "19:45", False),
    ("2023-10-07", "12:30", False),  # sábado: captura el viernes previo
])
def test_capture_ambiguity(date, time, amb):
    out = temporal.add_temporal_fields(_frame([date], [time]))
    assert bool(out["capture_rule_ambiguous"].iloc[0]) is amb


def test_unverifiable_when_no_time_on_friday_or_tuesday():
    out = temporal.add_temporal_fields(_frame(["2010-10-08", "2010-10-09"], [None, None]))
    assert list(out["capture_time_unverifiable"]) == [True, False]
    assert list(out["kickoff_precision"]) == ["date", "date"]
    assert out["pre_odds_capture_precision"].iloc[0] == "rule_based_date"


def test_kickoff_uk_to_utc_handles_bst():
    out = temporal.add_temporal_fields(_frame(["2023-08-12", "2023-12-09"], ["15:00", "15:00"]))
    utc = out["kickoff_at_utc"]
    assert utc.iloc[0].hour == 14 and utc.iloc[1].hour == 15  # BST (+1) vs GMT
    assert list(out["kickoff_precision"]) == ["minute", "minute"]


def test_deadline_strings():
    out = temporal.add_temporal_fields(_frame(["2023-10-07", "2023-10-04"], ["15:00", "19:45"]))
    assert list(out["pre_odds_capture_deadline_uk"]) == ["2023-10-06 17:00", "2023-10-03 13:00"]


def test_same_day_night_match_cannot_use_earlier_same_day_result():
    """Viernes 19:00 y viernes 21:00: el resultado del primero no puede alimentar al segundo (corte por
    fecha estricta; la hora no da orden fiable)."""
    from qsports import benchmark
    d = _frame(["2023-10-05", "2023-10-06", "2023-10-06"], ["19:45", "19:00", "21:00"])
    d["div"], d["over25"] = "X", [1.0, 1.0, 0.0]
    d = temporal.add_temporal_fields(d)
    p = benchmark.historical_frequency(d)
    assert p.iloc[2] == pytest.approx((1 + 1) / (1 + 2))  # solo el jueves cuenta; el de las 19:00 no


def test_capture_day_independent_of_kickoff_hour():
    """El día de captura depende solo de la fecha; la hora solo marca ambigüedad."""
    a = temporal.add_temporal_fields(_frame(["2023-10-06", "2023-10-06"], ["12:00", "20:00"]))
    assert a["pre_odds_capture_date_est"].nunique() == 1
    assert list(a["capture_rule_ambiguous"]) == [True, False]

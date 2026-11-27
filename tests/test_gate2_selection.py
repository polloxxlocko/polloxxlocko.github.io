"""Selección de hiperparámetros/variables: solo con el bloque de ajuste (exigencia 5)."""
import numpy as np
import pandas as pd
import pytest

from qsports import gate2, synthetic


@pytest.fixture(scope="module")
def frame():
    return synthetic.generate(n_divisions=1, n_teams=8, seasons=("0506", "0607", "1415"), seed=9)


def _preds(frame, seasons, rng):
    rows = frame[frame.season_code.isin(seasons)]
    out = []
    for cid, noise in (("A", 0.05), ("B", 0.2)):
        p = np.clip(rows["true_p_over"] + rng.normal(0, noise, len(rows)), 0.02, 0.98)
        out.append(pd.DataFrame({"match_id": rows["match_id"], "config_id": cid, "p_over": p}))
    return pd.concat(out)


def test_selection_refuses_inner_test_rows(frame):
    rng = np.random.default_rng(0)
    with pytest.raises(gate2.SelectionLeakError):
        gate2.select_best(_preds(frame, ["0607", "1415"], rng), frame, ["0506", "0607"])


def test_selection_invariant_to_inner_test_outcomes(frame):
    rng = np.random.default_rng(1)
    pr = _preds(frame, ["0506", "0607"], rng)
    best1, t1 = gate2.select_best(pr, frame, ["0506", "0607"])
    f2 = frame.copy()
    inner = f2.season_code == "1415"
    f2.loc[inner, "over25"] = 1 - f2.loc[inner, "over25"]
    best2, t2 = gate2.select_best(pr, f2, ["0506", "0607"])
    assert best1 == best2 == "A"
    pd.testing.assert_frame_equal(t1, t2)

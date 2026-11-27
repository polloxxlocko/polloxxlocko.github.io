"""Auditoría reproducible SIN datos de la fuente ni datos sellados (exigencia 8 de GATE 2).

`python -m qsports audit-synthetic` ejecuta el pipeline completo (benchmarks, features point-in-time,
walk-forward, M0-M4, evaluador, partición de decisión y una comprobación de invariancia al futuro) en
dos mundos sintéticos con verdad conocida:
  - mercado completo (ya incorpora la forma)      -> se espera que M4-sport NO supere a M4-cal;
  - mercado incompleto (ignora la forma)          -> se espera que M4-sport supere a M4-cal.
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

from . import benchmark, evaluation as ev, features, models, synthetic, walkforward as wf


def _prep(df: pd.DataFrame, hl: float = 5) -> pd.DataFrame:
    b = benchmark.market_benchmarks(df)
    df = df.assign(p_A_consensus=b["p_A_consensus"].values, A_consensus_valid=b["A_consensus_valid"].values)
    df["p_C_hist_freq"] = benchmark.historical_frequency(df)
    return pd.concat([df, features.build_features(df, hl)], axis=1)


def run_world(market_sees_form: bool, seed: int = 11) -> dict:
    t0 = time.perf_counter()
    df = _prep(synthetic.generate(n_divisions=3, n_teams=16, market_sees_form=market_sees_form, form_sd=0.3, seed=seed))
    seasons_all = ["0607", "0708", "0809", "0910", "1011", "1112", "1213"]
    ev_seasons = ["0910", "1011", "1112", "1213"]
    out_p = {}
    p1, l1 = wf.run(df, lambda: models.PoissonModel(window_days=730, ridge=4.0), seasons_all, label="M1")
    p2, l2 = wf.run(df, lambda: models.PoissonModel(half_life_days=240, ridge=4.0), seasons_all, label="M2")
    cols = features.feature_columns("GS")
    p3, l3 = wf.run(df, lambda: models.LogisticFeatureModel(cols, ridge=10), seasons_all, scope="pooled",
                    refit_every=6, label="M3")
    df = (df.merge(p2[["match_id", "p_over"]].rename(columns={"p_over": "inp_m2"}), on="match_id", how="left")
            .merge(p3[["match_id", "p_over"]].rename(columns={"p_over": "inp_m3"}), on="match_id", how="left"))
    sport = ["inp_m2", "inp_m3"]
    pc, lc = wf.run(df, lambda: models.MarketModel([], require_cols=sport), ev_seasons, scope="pooled", refit_every=6,
                    label="M4cal")
    ps, ls = wf.run(df, lambda: models.MarketModel(sport, ridge=10, require_cols=sport), ev_seasons, scope="pooled",
                    refit_every=6, label="M4sport")
    S = df[df.season_code.isin(ev_seasons)][["match_id", "match_date", "over25", "p_A_consensus", "p_C_hist_freq",
                                             "true_p_over"]]
    for k, p in (("M1", p1), ("M2", p2), ("M3", p3), ("M4cal", pc), ("M4sport", ps)):
        S = S.merge(p[["match_id", "p_over"]].rename(columns={"p_over": k}), on="match_id")
    S = S.dropna()
    res = {"market_sees_form": market_sees_form, "n": int(len(S)), "comparisons": {}}
    for a, b in [("M1", "p_C_hist_freq"), ("M2", "M1"), ("M4cal", "p_A_consensus"), ("M4sport", "p_A_consensus"),
                 ("M4sport", "M4cal"), ("true_p_over", "p_A_consensus")]:
        r = ev.compare(S.over25, S[a], S[b], S.match_date, delta=0.001, n_boot=2000)
        res["comparisons"][f"{a} - {b}"] = {"mean": round(r["delta_logloss"]["mean"], 5),
                                            "ci95": [round(r["delta_logloss"]["lo"], 5), round(r["delta_logloss"]["hi"], 5)],
                                            "category": r["category"]}
    logs = pd.concat([l1, l2, l3, lc, ls])
    res["fits"] = int(len(logs))
    res["nonconverged"] = int((~logs["converged"]).sum())
    res["seconds"] = round(time.perf_counter() - t0, 1)
    return res


def invariance_check(seed: int = 3) -> bool:
    df = _prep(synthetic.generate(n_divisions=2, n_teams=10, seasons=("0506", "0607", "0708"), seed=seed))
    tau0 = df.loc[df.season_code == "0607", "pre_odds_capture_date_est"].sort_values().iloc[60]
    d = df.copy()
    fut = d.match_date >= tau0
    rng = np.random.default_rng(0)
    for c in ["fthg", "ftag", "hs", "as_"]:
        d.loc[fut, c] = rng.permutation(d.loc[fut, c].to_numpy())
    d["total_goals"] = d.fthg + d.ftag
    d["over25"] = (d.total_goals > 2.5).astype(float)
    a, _ = wf.run(df, lambda: models.PoissonModel(half_life_days=240, ridge=4.0), ["0607"], label="inv")
    b, _ = wf.run(d, lambda: models.PoissonModel(half_life_days=240, ridge=4.0), ["0607"], label="inv")
    cap = df.set_index("match_id")["pre_odds_capture_date_est"]
    a, b = a[a.match_id.map(cap) <= tau0].set_index("match_id"), b[b.match_id.map(cap) <= tau0].set_index("match_id")
    return bool(np.array_equal(a.p_over.sort_index().values, b.loc[a.index].p_over.sort_index().values))


def main() -> dict:
    out = {"world_market_complete": run_world(True), "world_market_misses_form": run_world(False),
           "invariance_to_future_M2": invariance_check()}
    a = out["world_market_complete"]["comparisons"]["M4sport - M4cal"]["category"]
    b = out["world_market_misses_form"]["comparisons"]["M4sport - M4cal"]["category"]
    out["methodology_check"] = {"complete_market_no_false_incremental": a not in ("S-R", "S-NR"),
                                "incomplete_market_incremental_detected": b in ("S-R", "S-NR"),
                                "invariance_ok": out["invariance_to_future_M2"]}
    out["ok"] = all(out["methodology_check"].values())
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return out

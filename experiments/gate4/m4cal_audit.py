"""GATE 4: análisis de auditoría de M4-cal (sin abrir el holdout y sin repetir la evaluación de GATE 3).

Salidas en experiments/gate4/:
  m4cal_audit.json              coeficientes (a, b) a lo largo del tiempo, muestra de entrenamiento, efecto de la
                                máscara de `inp_m2`, rango de p_A, tamaño efectivo de muestra de los pesos
  gate3_nonconverged_fit.json   el único ajuste de M2 no convergente de GATE 3: reconstrucción con datos < τ, pulido,
                                y |Δp| máximo sobre todos los cruces de equipos (sin filas ni resultados de la validación)
  power_gate3.json              potencia para el holdout reestimada con los resultados de GATE 3
Uso: python experiments/gate4/m4cal_audit.py
"""
import importlib.util
import json
import math
import os
import sys
from pathlib import Path

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from qsports import evaluation as ev, gate2, gate3, holdout, models, paths  # noqa: E402
from qsports.ou import p_over25_poisson  # noqa: E402

ROOT = paths.ROOT
OUT = ROOT / "experiments" / "gate4"
REF = ROOT / "experiments" / "gate3" / "repro_run"
VAL = ROOT / "experiments" / "gate3" / "validation_run"


def coefficient_path():
    logs = [pd.read_parquet(REF / "fitlogs" / "M4cal" / f"M4cal__h730__{b}.parquet").assign(block=b) for b in ("tuning", "inner")]
    logs.append(pd.read_parquet(VAL / "fitlogs_M4cal.parquet").assign(block="validation_gate3"))
    L = pd.concat(logs, ignore_index=True)
    L = L[L["extra"].str.len() > 2].copy()
    ex = L["extra"].map(json.loads)
    L["a"], L["b"] = ex.map(lambda d: d["coef"][0]), ex.map(lambda d: d["coef"][1])
    L["n_used"] = ex.map(lambda d: d["n_train_used"])
    L["season"] = pd.to_datetime(L["fit_tau"]).map(lambda t: f"{(t.year if t.month >= 7 else t.year - 1) % 100:02d}"
                                                            f"{((t.year if t.month >= 7 else t.year - 1) + 1) % 100:02d}")
    by = L.groupby("season").agg(a_median=("a", "median"), b_median=("b", "median"), b_min=("b", "min"),
                                 b_max=("b", "max"), n_used_median=("n_used", "median"), fits=("a", "size"))
    return {"fits": int(len(L)), "nonconverged": int((~L["converged"]).sum()),
            "a_range": [float(L.a.min()), float(L.a.max())], "b_range": [float(L.b.min()), float(L.b.max())],
            "last_fit": {"fit_tau": str(L.iloc[-1]["fit_tau"]), "a": float(L.iloc[-1]["a"]), "b": float(L.iloc[-1]["b"]),
                         "n_used": int(L.iloc[-1]["n_used"])},
            "by_season": by.round(4).reset_index().to_dict("records")}


def mask_and_data():
    base = gate2.base_frame()
    spec_inputs = [REF / "predictions" / "M2" / f"M2__h480_r64__{b}.parquet" for b in ("tuning", "inner")]
    spec_inputs.append(VAL / "predictions_M2.parquet")
    inp = pd.concat([pd.read_parquet(f)[["match_id", "p_over"]] for f in spec_inputs], ignore_index=True)
    have = base["match_id"].isin(inp.loc[inp["p_over"].notna(), "match_id"])
    usable = base["p_A_consensus"].notna() & base["over25"].notna()
    seasons = base["season_code"]
    tab = pd.DataFrame({"season": seasons, "usable": usable, "with_inp": usable & have})
    by = tab.groupby("season")[["usable", "with_inp"]].sum()
    by["excluded_by_mask"] = by["usable"] - by["with_inp"]
    pa = base["p_A_consensus"].dropna()
    tau = pd.Timestamp("2024-08-02")  # fecha de referencia previa al holdout (solo datos < τ)
    t = base[usable & have & (base["match_date"] < tau)]
    w = np.exp(-math.log(2) * (tau - t["match_date"]).dt.days.to_numpy() / 730)
    return {"mask_by_season": by.reset_index().to_dict("records"),
            "rows_usable_0506_2324": int(by.loc[by.index >= "0506", "usable"].sum()),
            "rows_excluded_by_mask_0506_2324": int(by.loc[by.index >= "0506", "excluded_by_mask"].sum()),
            "p_A_range": [float(pa.min()), float(pa.max())], "clip_bounds": [1e-6, 1 - 1e-6],
            "weights_at_reference_tau": {"tau": str(tau.date()), "rows": int(len(t)), "sum_w": float(w.sum()),
                                         "effective_sample_size": float(w.sum() ** 2 / np.sum(w ** 2)),
                                         "share_weight_last_730d": float(w[(tau - t["match_date"]).dt.days < 730].sum() / w.sum())}}


def nonconverged_fit():
    spec = importlib.util.spec_from_file_location("cc", ROOT / "experiments" / "gate2_1" / "convergence_check.py")
    cc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cc)
    L = pd.read_parquet(VAL / "fitlogs_M2.parquet")
    nc = L[~L["converged"]]
    assert len(nc) == 1
    row = nc.iloc[0]
    div, tau = row["scope"], pd.Timestamp(row["fit_tau"])
    first_in_chain = str(L[L["scope"] == div]["fit_tau"].min()) == row["fit_tau"]
    base = gate2.base_frame()
    train = base[(base["div"] == div) & (base["match_date"] < tau)][
        ["match_id", "div", "season_code", "match_date", "pre_odds_capture_date_est", "home_team", "away_team", "fthg", "ftag"]]
    assert train["match_date"].max() < tau
    args = gate3.load_frozen()["candidates"]["M2"]["constructor_args"]
    m = cc.CheckedPoisson(**args)
    info = m.fit(train, tau)
    e = info["extra"]
    teams = list(m.params["att"].keys())
    pairs = pd.DataFrame([(h, a) for h in teams for a in teams if h != a], columns=["home_team", "away_team"])
    lh, la = m.intensities(pairs)
    p_std = p_over25_poisson(lh + la)
    saved = m.params
    m.params = m._strict
    lh2, la2 = m.intensities(pairs)
    m.params = saved
    p_str = p_over25_poisson(lh2 + la2)
    return {"div": div, "fit_tau": row["fit_tau"], "published_message": row["message"], "n_train_published": int(row["n_train"]),
            "n_train_reconstructed": int(len(train)), "first_fit_of_chain_cold_start": bool(first_in_chain),
            "reconstructed_message": info["message"], "reproduces_published_message": info["message"] == row["message"],
            "f_std_minus_f_strict": e["f_std"] - e["f_strict"], "gmax_std": e["gmax_std"], "gmax_strict": e["gmax_strict"],
            "strict_tol": e["strict_tol"], "strict_reached": e["strict_reached"], "dtheta_max": e["dtheta_max"],
            "team_pairs": int(len(pairs)), "max_abs_dp_over_all_pairs": float(np.max(np.abs(p_str - p_std))),
            "effect_on_M4cal": ("ninguno: M4-cal solo usa la DISPONIBILIDAD de inp_m2 para definir sus filas de "
                                "entrenamiento, y las predicciones de este ajuste existen con o sin pulido"),
            "validation_rows_or_outcomes_used": False}


def power():
    c = gate2.cfg()
    d = c["sesoi_nats"]
    R3 = json.loads((VAL / "results.json").read_text())["evaluation"]
    l0 = holdout.load_level0("holdout")
    n_h = int((l0.has_ou_pre_avg_pair & l0.ou_pre_avg_overround_in_range & ~l0.capture_rule_ambiguous
               & l0.has_result & ~l0.duplicate_key).sum())
    out = {"n_holdout_eligible_level0": n_h, "delta": d,
           "method": "se_holdout = se_bootstrap (semanas calendario, bloque 4) · sqrt(n_origen / n_holdout); Δ̂ ~ Normal"}
    g3 = R3["comparisons"]["M4cal-A"]
    se_v = g3["delta_logloss"]["se_boot"]
    se_h = se_v * math.sqrt(g3["n"] / n_h)
    thetas = {"0": 0.0, "GATE3_estimate": g3["delta_logloss"]["mean"], "minus_delta": -d, "minus_1.5delta": -1.5 * d}
    out["Q2_M4cal_minus_A"] = {
        "source": "GATE 3 (validación 2022/23-2023/24)", "se_validation": se_v, "n_validation": g3["n"], "se_holdout": se_h,
        "profile": ev.power_profile(se_h, d),
        "category_probabilities": {k: ev.prob_categories(t, se_h, d) for k, t in thetas.items()}}
    R2 = json.loads((REF / "results.json").read_text())["evaluate"]["comparisons"]["M4cal-A"]
    se_d = R2["delta_logloss"]["se_boot"] * math.sqrt(R2["n"] / n_h)
    out["Q2_M4cal_minus_A_development_for_comparison"] = {"se_holdout": se_d, "profile": ev.power_profile(se_d, d)}
    # Q1 (M4-cal − C): proxy de desarrollo (prueba interna, predicciones de la reproducción de referencia)
    base = gate2.base_frame()
    inner = c["blocks"]["inner_test_seasons"]
    U = gate2.universe(base, inner, "elig_A")
    p4 = pd.read_parquet(REF / "predictions" / "M4cal" / "M4cal__h730__inner.parquet")[["match_id", "p_over"]]
    S = U[["match_id", "match_date", "over25", "p_C_hist_freq"]].merge(p4, on="match_id", validate="one_to_one")
    r = ev.compare(S.over25, S.p_over, S.p_C_hist_freq, S.match_date, d, n_boot=2000, seed=20261127)
    se_q1 = r["delta_logloss"]["se_boot"] * math.sqrt(r["n"] / n_h)
    ac = R3["comparisons"]["A-C"]
    se_ac = ac["delta_logloss"]["se_boot"] * math.sqrt(ac["n"] / n_h)
    out["Q1_M4cal_minus_C"] = {
        "source": "desarrollo (prueba interna) y, como referencia, A − C de GATE 3",
        "development_mean": r["delta_logloss"]["mean"], "se_holdout_from_development": se_q1,
        "profile_from_development": ev.power_profile(se_q1, d),
        "gate3_A_minus_C_mean": ac["delta_logloss"]["mean"], "se_holdout_from_gate3_A_minus_C": se_ac,
        "P_S_R_if_theta_equals_gate3_A_minus_C": ev.prob_categories(ac["delta_logloss"]["mean"], se_ac, d)["S-R"]}
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = {"coefficients": coefficient_path(), "data_and_mask": mask_and_data()}
    (OUT / "m4cal_audit.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float))
    nc = nonconverged_fit()
    (OUT / "gate3_nonconverged_fit.json").write_text(json.dumps(nc, indent=1, ensure_ascii=False, default=float))
    pw = power()
    (OUT / "power_gate3.json").write_text(json.dumps(pw, indent=1, ensure_ascii=False, default=float))
    print(json.dumps({"coef": {k: v for k, v in res["coefficients"].items() if k != "by_season"},
                      "mask": {k: v for k, v in res["data_and_mask"].items() if k != "mask_by_season"},
                      "nonconverged": nc,
                      "power_Q2": {k: v for k, v in pw["Q2_M4cal_minus_A"]["profile"].items() if k != "assumption"},
                      "P_cat_Q2_at_GATE3": pw["Q2_M4cal_minus_A"]["category_probabilities"]["GATE3_estimate"],
                      "power_Q1": pw["Q1_M4cal_minus_C"]["profile_from_development"]["mde_superiority_relevant"],
                      "n_h": pw["n_holdout_eligible_level0"]}, indent=1, ensure_ascii=False, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())

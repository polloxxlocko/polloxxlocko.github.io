"""Estabilidad, convergencia y consumo computacional de GATE 2 (exigencia 7).
Uso: python experiments/gate2/stability.py --out DIR  -> DIR/stability.json
(DIR = directorio de una ejecución de run.py; el directorio publicado es de solo lectura)."""
import argparse
import json

import numpy as np
import pandas as pd

from qsports import gate2

_ap = argparse.ArgumentParser()
_ap.add_argument("--out", required=True)
gate2.configure(_ap.parse_args().out, "resume")
R = json.loads((gate2.OUT / "results.json").read_text())
reg = gate2._registry()
out = {}

# 1) Sensibilidad a configuraciones vecinas (bloque de ajuste): |Δp| medio y Δ log loss
sel = {"M1": R["poisson_tuning"]["M1_selected"], "M2": R["poisson_tuning"]["M2_selected"],
       "M3": R["m3_tuning"]["M3_selected"], "M4sport": R["m4"]["M4sport_selected"], "M4cal": R["m4"]["M4cal_selected"]}
nb = {}
for fam, cid in sel.items():
    P = gate2.load_preds(fam)
    P = P[P.block == "tuning"]
    w = P.pivot(index=["match_id"], columns="config_id", values="p_over").dropna()  # pivot falla ante duplicados
    hist = R["poisson_tuning"][f"{fam}_history"] if fam in ("M1", "M2") else (
        R["m3_tuning"]["M3_history"] if fam == "M3" else R["m4"][f"{fam}_history"])
    tab = {r["config_id"]: r["logloss"] for r in hist[-1]["table"]}
    rows = []
    for other in w.columns:
        if other == cid:
            continue
        rows.append({"config": other, "mean_abs_dp": float((w[other] - w[cid]).abs().mean()),
                     "delta_logloss_vs_selected": float(tab.get(other, np.nan) - tab.get(cid, np.nan))})
    rows.sort(key=lambda r: r["delta_logloss_vs_selected"])
    nb[fam] = {"selected": cid, "n_configs": int(w.shape[1]), "closest_by_logloss": rows[:3]}
out["neighbor_sensitivity_tuning"] = nb

# 2) Trayectorias de parámetros
L2 = gate2.load_fitlogs("M2")
L2 = L2[(L2.config_id == sel["M2"]) & (L2.extra.str.len() > 2)].copy()
ex = L2.extra.map(json.loads)
L2["eta"], L2["mu"] = ex.map(lambda d: d.get("eta")), ex.map(lambda d: d.get("mu"))
L2["season"] = pd.to_datetime(L2.fit_tau).map(lambda t: f"{(t.year if t.month >= 7 else t.year - 1) % 100:02d}")
g = L2.groupby(["scope", "season"])[["eta", "mu"]].median().reset_index()
out["M2_home_advantage_eta"] = {"by_division_median_over_time": g.groupby("scope")["eta"].median().round(4).to_dict(),
                                "overall_range": [float(g.eta.min()), float(g.eta.max())],
                                "season_median": g.groupby("season")["eta"].median().round(4).to_dict()}
out["M2_baseline_mu_exp_goals_per_team"] = {s: round(float(np.exp(v)), 3) for s, v in
                                            g.groupby("season")["mu"].median().items()}
for fam in ("M4cal", "M4sport"):
    L = gate2.load_fitlogs(fam)
    L = L[(L.config_id == sel[fam]) & (L.extra.str.len() > 2)]
    co = np.array([json.loads(x)["coef"] for x in L.extra])
    out[f"{fam}_coefficients_path"] = {"n_fits": int(len(co)), "a_range": [float(co[:, 0].min()), float(co[:, 0].max())],
                                       "b_range": [float(co[:, 1].min()), float(co[:, 1].max())],
                                       "b_last": float(co[-1, 1]),
                                       **({"beta_sport_range": [float(co[:, 2].min()), float(co[:, 2].max())]}
                                          if co.shape[1] > 2 else {})}

# 3) Convergencia y consumo
conv, comp = {}, {}
rl = json.loads((gate2.OUT / "runlog.json").read_text())
for fam, recs in rl.items():
    L = gate2.load_fitlogs(fam)
    L = L[L.wall_ms > 0] if "wall_ms" in L else L
    nc = L[~L.converged]
    gm = nc.message.str.extract(r"gmax=(\S+)")[0].astype(float) if len(nc) else pd.Series(dtype=float)
    conv[fam] = {"fits": int(len(L)), "nonconverged": int(len(nc)), "rate": round(len(nc) / max(len(L), 1), 6),
                 "nonconv_gmax_max": float(gm.max()) if len(gm) else None,
                 "messages": nc.message.str.replace(r"gmax=\S+\s*", "", regex=True).value_counts().head(3).to_dict()}
    comp[fam] = {"config_runs": len(recs), "wall_s_total": round(sum(r["wall_s"] for r in recs), 1),
                 "sum_fit_s_total": round(sum(r["sum_fit_s"] for r in recs), 1),
                 "fit_ms_median": round(float(L.wall_ms.median()), 2) if len(L) else None,
                 "fit_ms_p99": round(float(L.wall_ms.quantile(.99)), 2) if len(L) else None,
                 "max_rss_main_mb": max(r["max_rss_main_mb"] for r in recs),
                 "nan_predictions": int(sum(r["n_nan_preds"] for r in recs))}
out["convergence"] = conv
out["compute"] = comp
out["convergence_note"] = ("Ajustes Poisson marcados sin convergencia: verificación individual de TODOS los casos en "
                           "experiments/gate2_1/convergence_check.json (GATE 2.1, exigencia 5).")
(gate2.OUT / "stability.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float))
print(json.dumps({k: out[k] for k in ("convergence", "compute")}, indent=1, default=float))
print(json.dumps(out["neighbor_sensitivity_tuning"], indent=0, default=float)[:1500])
print("eta", out["M2_home_advantage_eta"]["overall_range"], out["M2_home_advantage_eta"]["season_median"])
print({k: v for k, v in out.items() if k.endswith("coefficients_path")})

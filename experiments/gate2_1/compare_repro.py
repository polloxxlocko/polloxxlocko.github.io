"""GATE 2.1: compara una ejecución limpia de run.py con los resultados publicados de GATE 2 (solo lectura).

Uso: python experiments/gate2_1/compare_repro.py --repro DIR [--out experiments/gate2_1/repro_comparison.json]

Compara:
1. Conjunto de configuraciones por familia y bloque (incluida la ruta de extensión de grilla D-1).
2. Predicciones fuera de muestra fila a fila (unión 1:1 por match_id): filas, igualdad bit a bit de p_over,
   máxima diferencia absoluta, fit_tau, λ.
3. Registros de ajuste: número de ajustes, ajustes no convergentes, n_train y train_max_date por ajuste.
4. Selecciones y decisiones de la escalera; tablas de selección (log loss).
5. Comparaciones de la prueba interna: método publicado (semanas activas) reproducido frente a lo publicado, y
   método corregido (semanas calendario) frente a lo publicado.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from qsports import gate2, paths, validation as val

PUB = paths.ROOT / "experiments" / "gate2"


def _pub_preds(fam):
    files = sorted((PUB / "predictions" / fam).glob("*.parquet"))
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def _rep_preds(rep, fam):
    files = sorted((rep / "predictions" / fam).glob("*.parquet"))
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True) if files else pd.DataFrame()


def _rep_logs(rep, fam):
    files = sorted((rep / "fitlogs" / fam).glob("*.parquet"))
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True) if files else pd.DataFrame()


def compare_predictions(rep):
    out, fams = [], sorted(p.name for p in (PUB / "predictions").iterdir() if p.is_dir())
    for fam in fams:
        A, B = _pub_preds(fam), _rep_preds(rep, fam)
        keys_a = set(map(tuple, A[["config_id", "block"]].drop_duplicates().to_numpy()))
        keys_b = set(map(tuple, B[["config_id", "block"]].drop_duplicates().to_numpy())) if len(B) else set()
        for cid, block in sorted(keys_a | keys_b):
            a = A[(A.config_id == cid) & (A.block == block)]
            b = B[(B.config_id == cid) & (B.block == block)] if len(B) else B
            rec = {"family": fam, "config_id": cid, "block": block, "n_published": int(len(a)), "n_repro": int(len(b))}
            if len(a) and len(b):
                val.unique_ids(a, "match_id", f"pub:{cid}:{block}")
                val.unique_ids(b, "match_id", f"rep:{cid}:{block}")
                m = a.merge(b, on="match_id", how="outer", suffixes=("_p", "_r"), validate="one_to_one", indicator=True)
                both = m["_merge"] == "both"
                pa, pr = m.loc[both, "p_over_p"], m.loc[both, "p_over_r"]
                eq = (pa == pr) | (pa.isna() & pr.isna())
                rec.update(only_published=int((m["_merge"] == "left_only").sum()),
                           only_repro=int((m["_merge"] == "right_only").sum()),
                           p_over_bitwise_equal=int(eq.sum()), p_over_not_equal=int((~eq).sum()),
                           max_abs_diff=float(np.nanmax(np.abs(pa - pr))) if (~(pa.isna() & pr.isna())).any() else 0.0,
                           fit_tau_equal=bool((pd.to_datetime(m.loc[both, "fit_tau_p"]) ==
                                               pd.to_datetime(m.loc[both, "fit_tau_r"])).all()))
                for lam in ("lam_h", "lam_a"):
                    if f"{lam}_p" in m:
                        d = (m.loc[both, f"{lam}_p"].astype(float) - m.loc[both, f"{lam}_r"].astype(float)).abs()
                        rec[f"{lam}_max_abs_diff"] = float(d.max()) if d.notna().any() else 0.0
            out.append(rec)
    return pd.DataFrame(out)


def compare_fitlogs(rep):
    out = []
    for fam in sorted(p.stem for p in (PUB / "fitlogs").glob("*.parquet")):
        A = pd.read_parquet(PUB / "fitlogs" / f"{fam}.parquet")
        B = _rep_logs(rep, fam)
        if "scope" not in A or not len(B):
            out.append({"family": fam, "comparable": False})
            continue
        for (cid, block), a in A.groupby(["config_id", "block"]):
            b = B[(B.config_id == cid) & (B.block == block)]
            k = ["scope", "fit_tau"]
            m = a.merge(b, on=k, how="outer", suffixes=("_p", "_r"), indicator=True)
            both = m["_merge"] == "both"
            out.append({"family": fam, "config_id": cid, "block": block, "fits_published": int(len(a)),
                        "fits_repro": int(len(b)), "unmatched": int((~both).sum()),
                        "nonconverged_published": int((~a["converged"]).sum()),
                        "nonconverged_repro": int((~b["converged"]).sum()) if len(b) else None,
                        "n_train_equal": bool((m.loc[both, "n_train_p"] == m.loc[both, "n_train_r"]).all()),
                        "train_max_date_equal": bool((m.loc[both, "train_max_date_p"] == m.loc[both, "train_max_date_r"]).all()),
                        "converged_flags_equal": bool((m.loc[both, "converged_p"] == m.loc[both, "converged_r"]).all())})
    return pd.DataFrame(out)


def compare_results(rep):
    P = json.loads((PUB / "results.json").read_text())
    R = json.loads((rep / "results.json").read_text())
    sel_keys = {"poisson_tuning": ["M1_selected", "M2_selected_stage1", "M2_promoted_candidate", "M2_selected", "M2_justified"],
                "m3_tuning": ["M3_selected", "best_goals_only", "best_with_shots", "shots_enter_M4_sport"],
                "m4": ["sport_cols", "M4cal_selected", "M4sport_selected"]}
    sel = {}
    for st, ks in sel_keys.items():
        for k in ks:
            sel[f"{st}.{k}"] = {"published": P[st].get(k), "repro": R[st].get(k), "equal": P[st].get(k) == R[st].get(k)}
    for k in ("M2_justified_legacy_active_weeks",):
        sel[f"poisson_tuning.{k}"] = {"repro": R["poisson_tuning"].get(k)}
    sel["m3_tuning.shots_enter_M4_sport_legacy_active_weeks"] = {"repro": R["m3_tuning"].get("shots_enter_M4_sport_legacy_active_weeks")}
    hist = {}
    for st, hk in (("poisson_tuning", "M1_history"), ("poisson_tuning", "M2_history"), ("m3_tuning", "M3_history"),
                   ("m4", "M4cal_history"), ("m4", "M4sport_history")):
        hp, hr = P[st][hk], R[st][hk]
        same_path = [h["grid"] for h in hp] == [h["grid"] for h in hr] and [h["best"] for h in hp] == [h["best"] for h in hr]
        diffs = []
        for a, b in zip(hp, hr):
            ta = {r["config_id"]: r["logloss"] for r in a["table"]}
            tb = {r["config_id"]: r["logloss"] for r in b["table"]}
            diffs += [abs(ta[c] - tb[c]) for c in ta if c in tb]
        hist[hk] = {"same_grid_path_and_best": same_path, "steps": len(hp),
                    "max_abs_logloss_diff": float(max(diffs)) if diffs else None}
    cmpd = {}
    pe, re_ = P["evaluate"], R["evaluate"]
    for k, v in pe["comparisons"].items():
        rl = re_["comparisons_gate2_method_active_weeks"][k]
        rc = re_["comparisons"][k]
        cmpd[k] = {"published": {x: v["delta_logloss"][x] for x in ("mean", "lo", "hi")} | {"category": v["category"]},
                   "repro_same_method": {x: rl["delta_logloss"][x] for x in ("mean", "lo", "hi")} | {"category": rl["category"]},
                   "repro_calendar_weeks": {x: rc["delta_logloss"][x] for x in ("mean", "lo", "hi")} | {"category": rc["category"]},
                   "same_method_max_abs_diff": max(abs(v["delta_logloss"][x] - rl["delta_logloss"][x]) for x in ("mean", "lo", "hi")),
                   "same_method_category_equal": v["category"] == rl["category"],
                   "calendar_category_equal_to_published": v["category"] == rc["category"]}
    other = {"n_primary": {"published": pe["n_primary"], "repro": re_["n_primary"]},
             "M5_diagnostics": {"published": pe["M5_diagnostics"], "repro": re_["M5_diagnostics"]},
             "power_n_holdout": {"published": pe["power"]["n_holdout_eligible_level0"],
                                 "repro": re_["power"]["n_holdout_eligible_level0"]}}
    return sel, hist, cmpd, other


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repro", required=True)
    ap.add_argument("--out", default=str(paths.ROOT / "experiments" / "gate2_1" / "repro_comparison.json"))
    a = ap.parse_args()
    rep = Path(a.repro)
    man = json.loads((rep / "RUN_MANIFEST.json").read_text())
    PR = compare_predictions(rep)
    FL = compare_fitlogs(rep)
    sel, hist, cmpd, other = compare_results(rep)
    pr_ok = PR.dropna(subset=["p_over_not_equal"]) if "p_over_not_equal" in PR else PR
    summary = {
        "repro_dir_manifest": {k: man.get(k) for k in ("git_commit", "git_dirty", "clean", "code_hash", "dataset",
                                                       "started_utc", "finished_utc", "wall_s", "sealed_unchanged",
                                                       "artifacts_set_sha256")},
        "configs_published": int(len(PR[PR.n_published > 0])), "configs_repro": int(len(PR[PR.n_repro > 0])),
        "configs_only_published": PR[(PR.n_published > 0) & (PR.n_repro == 0)][["family", "config_id", "block"]].to_dict("records"),
        "configs_only_repro": PR[(PR.n_repro > 0) & (PR.n_published == 0)][["family", "config_id", "block"]].to_dict("records"),
        "prediction_rows_compared": int(pr_ok.get("p_over_bitwise_equal", pd.Series(dtype=int)).sum()
                                        + pr_ok.get("p_over_not_equal", pd.Series(dtype=int)).sum()),
        "prediction_rows_not_bitwise_equal": int(pr_ok.get("p_over_not_equal", pd.Series(dtype=int)).sum()),
        "prediction_max_abs_diff": float(pr_ok.get("max_abs_diff", pd.Series([0.0])).max()),
        "prediction_rows_only_one_side": int(pr_ok.get("only_published", pd.Series(dtype=int)).sum()
                                             + pr_ok.get("only_repro", pd.Series(dtype=int)).sum()),
        "fitlogs_all_flags_equal": bool(FL.get("converged_flags_equal", pd.Series([True])).all()),
        "fitlogs_nonconverged_published": int(FL.get("nonconverged_published", pd.Series(dtype=int)).sum()),
        "fitlogs_nonconverged_repro": int(FL.get("nonconverged_repro", pd.Series(dtype=float)).fillna(0).sum()),
        "fitlogs_train_max_date_equal": bool(FL.get("train_max_date_equal", pd.Series([True])).all()),
        "selections_all_equal": all(v.get("equal", True) for v in sel.values()),
        "grid_paths_all_equal": all(v["same_grid_path_and_best"] for v in hist.values()),
        "inner_same_method_max_abs_diff": max(v["same_method_max_abs_diff"] for v in cmpd.values()),
        "inner_same_method_categories_equal": all(v["same_method_category_equal"] for v in cmpd.values()),
        "inner_calendar_categories_changed": [k for k, v in cmpd.items() if not v["calendar_category_equal_to_published"]],
        "script_sha256": gate2.sha256_file(Path(__file__)),
    }
    res = {"summary": summary, "selections": sel, "grid_histories": hist, "inner_comparisons": cmpd, "other": other,
           "predictions": PR.to_dict("records"), "fitlogs": FL.to_dict("records")}
    Path(a.out).write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float))
    print(json.dumps(summary, indent=1, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()

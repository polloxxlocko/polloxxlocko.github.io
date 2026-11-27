"""Compara dos reproducciones limpias (formato GATE 2.1: un archivo por configuración y bloque).

Uso: python experiments/gate3_analysis/compare_repros.py --old experiments/gate2_1/repro_run --new experiments/gate3/repro_run
Salida: experiments/gate3/repro_comparison_vs_gate2_1.json
Comprueba en particular que las decisiones y predicciones de los candidatos seleccionados no cambian tras la
corrección del prior de ascendidos (solo deberían cambiar las configuraciones `_pp`).
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from qsports import gate2, paths

CANDIDATES = {"M2": "M2__h480_r64", "M4cal": "M4cal__h730", "M4sport": "M4sport__h730_r1000"}


def preds(d: Path):
    out = {}
    for f in sorted((d / "predictions").glob("*/*.parquet")):
        out[(f.parent.name, f.stem)] = f
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--out", default=str(paths.ROOT / "experiments" / "gate3" / "repro_comparison_vs_gate2_1.json"))
    a = ap.parse_args()
    old, new = Path(a.old).resolve(), Path(a.new).resolve()
    po, pn = preds(old), preds(new)
    rows = []
    for key in sorted(set(po) | set(pn)):
        rec = {"family": key[0], "file": key[1], "in_old": key in po, "in_new": key in pn}
        if key in po and key in pn:
            A, B = pd.read_parquet(po[key]), pd.read_parquet(pn[key])
            m = A.merge(B, on="match_id", how="outer", suffixes=("_o", "_n"), validate="one_to_one", indicator=True)
            both = m["_merge"] == "both"
            eq = (m.loc[both, "p_over_o"] == m.loc[both, "p_over_n"]) | (m.loc[both, "p_over_o"].isna() & m.loc[both, "p_over_n"].isna())
            rec.update(rows=int(len(m)), one_side=int((~both).sum()), bitwise_equal=int(eq.sum()), not_equal=int((~eq).sum()),
                       max_abs_diff=float(np.nanmax(np.abs(m.loc[both, "p_over_o"] - m.loc[both, "p_over_n"])))
                       if (~eq).any() else 0.0, file_sha256_equal=gate2.sha256_file(po[key]) == gate2.sha256_file(pn[key]))
        rows.append(rec)
    T = pd.DataFrame(rows)
    Ro, Rn = json.loads((old / "results.json").read_text()), json.loads((new / "results.json").read_text())
    keys = {"poisson_tuning": ["M1_selected", "M2_selected_stage1", "M2_promoted_candidate", "M2_selected", "M2_justified"],
            "m3_tuning": ["M3_selected", "best_goals_only", "best_with_shots", "shots_enter_M4_sport"],
            "m4": ["sport_cols", "M4cal_selected", "M4sport_selected"],
            "m3_spec_sensitivity": ["M3log_selected", "H1b_decision_unchanged"]}
    dec = {f"{s}.{k}": {"old": Ro.get(s, {}).get(k), "new": Rn.get(s, {}).get(k),
                        "equal": Ro.get(s, {}).get(k) == Rn.get(s, {}).get(k)} for s, ks in keys.items() for k in ks}
    stage2 = {"old": Ro["poisson_tuning"]["M2_stage2_table"], "new": Rn["poisson_tuning"]["M2_stage2_table"]}
    inner = {}
    for k, v in Ro["evaluate"]["comparisons"].items():
        w = Rn["evaluate"]["comparisons"][k]
        inner[k] = {"old": [v["delta_logloss"][x] for x in ("mean", "lo", "hi")] + [v["category"]],
                    "new": [w["delta_logloss"][x] for x in ("mean", "lo", "hi")] + [w["category"]],
                    "identical": [v["delta_logloss"][x] for x in ("mean", "lo", "hi")] == [w["delta_logloss"][x] for x in ("mean", "lo", "hi")]
                    and v["category"] == w["category"]}
    cand = T[T["file"].str.replace(r"__(tuning|inner)$", "", regex=True).isin(CANDIDATES.values())]
    changed = T[(T.get("not_equal", 0) > 0)]
    summary = {
        "old": str(old.relative_to(paths.ROOT)), "new": str(new.relative_to(paths.ROOT)),
        "old_commit": json.loads((old / "RUN_MANIFEST.json").read_text())["git_commit"],
        "new_commit": json.loads((new / "RUN_MANIFEST.json").read_text())["git_commit"],
        "files_compared": int(T["rows"].notna().sum()), "files_only_one_side": int((~(T.in_old & T.in_new)).sum()),
        "rows_compared": int(T["rows"].sum()), "rows_not_equal": int(T["not_equal"].sum()),
        "files_with_differences": changed[["family", "file", "not_equal", "max_abs_diff"]].to_dict("records"),
        "candidate_files": cand[["family", "file", "rows", "bitwise_equal", "not_equal", "file_sha256_equal"]].to_dict("records"),
        "candidates_bitwise_identical": bool((cand["not_equal"] == 0).all() and len(cand) == 6),
        "decisions_all_equal": all(v["equal"] for v in dec.values()),
        "inner_comparisons_identical": all(v["identical"] for v in inner.values()),
        "script_sha256": gate2.sha256_file(Path(__file__)),
    }
    res = {"summary": summary, "decisions": dec, "M2_stage2_table": stage2, "inner_comparisons": inner,
           "files": T.to_dict("records")}
    Path(a.out).write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float))
    print(json.dumps(summary, indent=1, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()

"""Inventario, calidad, exclusiones, diagnósticos temporales y de Pinnacle (GATE 1).

Regla de acceso: el inventario usa SOLO metadatos de nivel 0 para todas las particiones.
Los chequeos que dependen de valores (goles, cuotas, nombres) usan SOLO desarrollo.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import benchmark, holdout, paths, process
from .divisions import DIVISIONS

OUT = paths.REPORTS_GATE1


def _pct(s: pd.Series) -> float:
    return round(float(s.mean()) * 100, 1) if len(s) else float("nan")


# ---------------------------------------------------------------- inventario (nivel 0)
def _all_level0() -> pd.DataFrame:
    dev = pd.read_parquet(paths.PROCESSED_DEV / "metadata_level0.parquet")
    dev["partition"] = "dev"
    parts = [dev]
    for p in ("holdout", "prospective"):
        x = holdout.load_level0(p)
        x["partition"] = p
        parts.append(x)
    return pd.concat(parts, ignore_index=True)


def _file_reports() -> pd.DataFrame:
    reps = json.loads((paths.PROCESSED_DEV / "file_reports.json").read_text())
    for p in ("holdout", "prospective"):
        reps += holdout.registry(p)["file_reports_level0"]
    fr = pd.DataFrame([r for r in reps if "div" in r])
    return fr


def inventory() -> tuple[pd.DataFrame, pd.DataFrame]:
    l0 = _all_level0()
    fr = _file_reports().set_index(["div", "season_code"])
    l0["elig_A_level0"] = (l0["has_ou_pre_avg_pair"] & l0["ou_pre_avg_overround_in_range"]
                           & ~l0["capture_rule_ambiguous"] & l0["has_result"] & ~l0["duplicate_key"])
    rows = []
    for (div, sc), g in l0.groupby(["div", "season_code"]):
        r = {"div": div, "country": DIVISIONS[div]["country"], "competition": DIVISIONS[div]["competition"],
             "season_code": sc, "season": g["season"].iloc[0], "partition": g["partition"].iloc[0],
             "n_rows": len(g), "n_with_result": int(g["has_result"].sum()),
             "pct_missing_result": round(100 - _pct(g["has_result"]), 2)}
        for p in ["ou_pre_avg", "ou_pre_b365", "ou_pre_pin", "ou_pre_gb", "ou_pre_max",
                  "ou_close_avg", "ou_close_b365", "ou_close_pin", "ou_close_max"]:
            r[f"pct_{p}"] = _pct(g[f"has_{p}_pair"])
        r["pct_ou_pre_any_single_or_avg"] = _pct(g[["has_ou_pre_avg_pair", "has_ou_pre_b365_pair",
                                                     "has_ou_pre_pin_pair", "has_ou_pre_gb_pair"]].any(axis=1))
        r["pct_ou_close_any"] = _pct(g[["has_ou_close_avg_pair", "has_ou_close_b365_pair",
                                        "has_ou_close_pin_pair"]].any(axis=1))
        src = g["ou_pre_avg_source"].dropna().unique().tolist()
        r["ou_pre_avg_source"] = "+".join(sorted(src)) if src else ""
        r["pct_eligible_A_level0"] = _pct(g["elig_A_level0"])
        for t in ["x12_pre_b365", "x12_pre_pin", "x12_pre_avg", "x12_close_avg"]:
            r[f"pct_{t}"] = _pct(g[f"has_{t}"])
        for s in ["halftime", "shots", "shots_target", "corners", "fouls", "yellow", "red", "referee", "xg",
                  "attendance"]:
            r[f"pct_{s}"] = _pct(g[f"has_{s}"])
        r["pct_kickoff_time"] = _pct(g["kickoff_precision"] == "minute")
        r["pct_capture_ambiguous"] = _pct(g["capture_rule_ambiguous"])
        r["pct_capture_time_unverifiable"] = _pct(g["capture_time_unverifiable"])
        r["n_duplicate_key"] = int(g["duplicate_key"].sum())
        r["n_unparsed_date"] = int(g["match_date"].isna().sum())
        if (div, sc) in fr.index:
            f = fr.loc[(div, sc)]
            r["encoding"] = f["encoding"]
            r["rows_wider_than_header"] = int(f["rows_wider_than_header"])
            r["duplicate_header_names"] = ",".join(f["duplicate_header_names"]) if isinstance(
                f["duplicate_header_names"], list) else ""
            bk = f["bookmakers_in_header"]
            r["books_x12_pre"] = ",".join(bk["x12_pre"])
            r["books_ou_pre"] = ",".join(bk["ou_pre"])
            r["books_ou_close"] = ",".join(bk["ou_close"])
        rows.append(r)
    inv = pd.DataFrame(rows).sort_values(["div", "season_code"])
    # resumen por división
    summ = []
    for div, g in inv.groupby("div", sort=False):
        d = g[g.partition == "dev"]
        w = d["n_rows"]
        wavg = lambda c: round(float(np.average(d[c], weights=w)), 1)
        d19 = d[d.season_code >= "1920"]
        summ.append({
            "div": div, "country": DIVISIONS[div]["country"], "competition": DIVISIONS[div]["competition"],
            "seasons_available": f"{g.season.iloc[0]}–{g.season.iloc[-1]} ({len(g)})",
            "n_dev": int(d.n_rows.sum()), "n_holdout": int(g[g.partition == "holdout"].n_rows.sum()),
            "n_prospective": int(g[g.partition == "prospective"].n_rows.sum()),
            "dev_pct_ou_pre_any_0506+": round(float(np.average(d[d.season_code >= "0506"].pct_ou_pre_any_single_or_avg,
                                                                weights=d[d.season_code >= "0506"].n_rows)), 1),
            "dev_pct_ou_close_1920+": round(float(np.average(d19.pct_ou_close_any, weights=d19.n_rows)), 1) if len(d19) else None,
            "dev_pct_eligible_A_0506+": round(float(np.average(d[d.season_code >= "0506"].pct_eligible_A_level0,
                                                               weights=d[d.season_code >= "0506"].n_rows)), 1),
            "dev_pct_shots": wavg("pct_shots"), "dev_pct_corners": wavg("pct_corners"),
            "dev_pct_referee": wavg("pct_referee"), "dev_pct_missing_result": wavg("pct_missing_result"),
            "first_season_shots_ge90": next((s for s, v in zip(d.season, d.pct_shots) if v >= 90), None),
            "rows_wider_total": int(g.get("rows_wider_than_header", pd.Series(0)).fillna(0).sum()),
            "encodings": ",".join(sorted(g["encoding"].dropna().unique())),
        })
    return inv, pd.DataFrame(summ)


# ---------------------------------------------------------------- calidad (valores, solo dev)
def quality_dev(dev: pd.DataFrame) -> dict:
    q: dict = {}
    res = dev[dev["fthg"].notna()]
    q["n_dev_rows"] = int(len(dev))
    q["rows_without_result"] = dev.loc[dev["fthg"].isna(), ["season_code", "div", "source_file", "source_row",
                                                             "home_team", "away_team"]].astype(str).to_dict("records")
    exp_ftr = np.where(res.fthg > res.ftag, "H", np.where(res.fthg < res.ftag, "A", "D"))
    q["ftr_inconsistent"] = int((res["ftr"].astype(str) != exp_ftr).sum())
    ht = res[res.hthg.notna() & res.htag.notna()]
    q["ht_goals_gt_ft_goals"] = int(((ht.hthg > ht.fthg) | (ht.htag > ht.ftag)).sum())
    exp_htr = np.where(ht.hthg > ht.htag, "H", np.where(ht.hthg < ht.htag, "A", "D"))
    q["htr_inconsistent"] = int((ht["htr"].notna() & (ht["htr"].astype(str) != exp_htr)).sum())
    q["goals_out_of_range_0_15"] = int(((res.fthg < 0) | (res.fthg > 15) | (res.ftag < 0) | (res.ftag > 15)).sum())
    q["non_integer_goals"] = int(((res.fthg % 1 != 0) | (res.ftag % 1 != 0)).sum())
    st = dev
    q["shots_on_target_gt_shots"] = int(((st.hst > st.hs) | (st.ast > st.as_)).sum())
    q["red_cards_gt_5"] = int(((st.hr > 5) | (st.ar > 5)).sum())
    q["corners_gt_30"] = int(((st.hc > 30) | (st.ac > 30)).sum())
    # cuotas
    odd_cols = [c for c in dev.columns if c.startswith(("ou_", "x12_")) and dev[c].dtype.kind == "f"
                and not c.endswith("n_books")]
    q["odds_below_1_01"] = {c: int(((dev[c] < 1.01) & dev[c].notna()).sum()) for c in odd_cols
                            if ((dev[c] < 1.01) & dev[c].notna()).any()}
    ovr = {}
    for p in ["ou_pre_avg", "ou_pre_b365", "ou_pre_pin", "ou_pre_gb", "ou_close_avg", "ou_close_b365", "ou_close_pin",
              "ou_pre_max", "ou_close_max"]:
        o, u = dev[f"{p}_over"], dev[f"{p}_under"]
        m = (o >= 1.01) & (u >= 1.01)
        if m.sum() == 0:
            continue
        ov = 1 / o[m] + 1 / u[m] - 1
        ovr[p] = {"n": int(m.sum()), "median": round(float(ov.median()), 4), "p01": round(float(ov.quantile(.01)), 4),
                  "p99": round(float(ov.quantile(.99)), 4), "n_lt_0": int((ov < 0).sum()), "n_gt_0_25": int((ov > .25).sum())}
    q["ou_overround_by_pair"] = ovr
    reg = {}
    for src in ("betbrain", "oddsportal"):
        mm = (dev.ou_pre_avg_source == src) & (dev.ou_pre_avg_over >= 1.01) & (dev.ou_pre_avg_under >= 1.01)
        ov = 1 / dev.ou_pre_avg_over[mm] + 1 / dev.ou_pre_avg_under[mm] - 1
        reg[src] = {"n": int(mm.sum()), "median": round(float(ov.median()), 4), "seasons": f"{dev.season_code[mm].min()}-{dev.season_code[mm].max()}"}
    q["ou_pre_avg_overround_by_regime"] = reg
    # artefactos y valores no numéricos
    reps = json.loads((paths.PROCESSED_DEV / "file_reports.json").read_text())
    q["non_numeric_values_by_file"] = {f"{r['season_code']}/{r['div']}": r["non_numeric_values"] for r in reps
                                       if r.get("non_numeric_values")}
    q["files_with_rows_wider_than_header"] = {f"{r['season_code']}/{r['div']}": r["rows_wider_than_header"]
                                              for r in reps if r.get("rows_wider_than_header")}
    q["files_with_duplicate_header_names"] = {f"{r['season_code']}/{r['div']}": r["duplicate_header_names"]
                                              for r in reps if r.get("duplicate_header_names")}
    q["date_outside_season_window"] = int((~dev.date_in_season_window & dev.match_date.notna()).sum())
    q["unparsed_dates"] = int(dev.match_date.isna().sum())
    # equipos
    teams = pd.concat([dev[["div", "country", "season_code", "home_team"]].rename(columns={"home_team": "team"}),
                       dev[["div", "country", "season_code", "away_team"]].rename(columns={"away_team": "team"})]).dropna()
    per_ds = teams.groupby(["div", "season_code"])["team"].nunique()
    q["teams_per_division_season"] = {"min": int(per_ds.min()), "max": int(per_ds.max()),
                                      "min_at": "/".join(per_ds.idxmin()), "max_at": "/".join(per_ds.idxmax())}
    cnt = teams.groupby(["div", "season_code", "team"]).size()
    low = cnt[cnt < 10]
    q["team_seasons_with_lt_10_appearances"] = [f"{d}/{s}/{t}: {n}" for (d, s, t), n in low.items()]
    names = pd.Series(teams["team"].unique())
    norm = names.str.lower().str.replace(r"[^a-z0-9]", "", regex=True)
    coll = names.groupby(norm).agg(list)
    q["team_name_variant_collisions"] = [v for v in coll if len(v) > 1]
    q["non_ascii_team_names"] = sorted([n for n in names if not n.isascii()])
    multi_country = teams.groupby("team")["country"].nunique()
    q["team_names_in_multiple_countries"] = sorted(multi_country[multi_country > 1].index.tolist())
    return q


# ---------------------------------------------------------------- exclusiones
def apply_exclusions(dev: pd.DataFrame, bench: pd.DataFrame) -> dict:
    crit = json.loads((paths.CONFIGS / "exclusion_criteria.json").read_text())
    req = crit["training_universe"]["require_fields"]
    train_ok = np.logical_and.reduce([dev[c].notna().values for c in req]) & ~dev["duplicate_key"].values
    mA = crit["market_comparison_A"]
    eligA = (train_ok & bench["A_consensus_valid"].values & ~dev["capture_rule_ambiguous"].values
             & (dev["season_code"].values >= mA["first_season"]))
    df = pd.DataFrame({"div": dev["div"], "season_code": dev["season_code"], "train": train_ok, "eligA": eligA})
    ds = df[df.season_code >= mA["first_season"]].groupby(["div", "season_code"]).agg(
        n=("train", "size"), n_train=("train", "sum"), n_eligA=("eligA", "sum"))
    ds["frac_eligA"] = ds.n_eligA / ds.n
    ds["meets_min"] = ds.frac_eligA >= crit["division_season_market_A"]["min_eligible_fraction"]
    div_ok = ds.groupby("div")["meets_min"].any()
    reasons = pd.Series(np.select(
        [~dev["match_date"].notna(), ~dev["home_team"].notna(), ~dev["fthg"].notna(), dev["duplicate_key"]],
        ["fecha_no_parseable", "equipo_faltante", "resultado_faltante", "clave_duplicada"], default=""))
    return {
        "training_universe_rows": int(train_ok.sum()),
        "training_excluded": reasons[~train_ok].value_counts().to_dict(),
        "market_A_eligible_rows_0506_2324": int(eligA.sum()),
        "market_A_excluded_reasons_0506+": bench.loc[(dev.season_code >= "0506").values & train_ok,
                                                     "A_consensus_invalid_reason"].replace("", "valido").value_counts().to_dict(),
        "market_A_excluded_capture_ambiguous": int((train_ok & bench["A_consensus_valid"].values
                                                    & dev["capture_rule_ambiguous"].values
                                                    & (dev.season_code.values >= "0506")).sum()),
        "division_seasons_below_min": ds[~ds.meets_min].reset_index()[["div", "season_code", "frac_eligA"]].round(3).to_dict("records"),
        "divisions_excluded_from_market_universe": sorted(div_ok[~div_ok].index.tolist()),
        "by_division_season": ds.reset_index(),
    }


# ---------------------------------------------------------------- temporal (dev)
def temporal_diagnostics(dev: pd.DataFrame, bench: pd.DataFrame) -> dict:
    t: dict = {}
    d19 = dev[dev.season_code >= "1920"].copy()
    sat = d19[d19.weekday == 5]
    t["saturday_modal_kickoff_uk_by_div"] = sat.groupby("div")["kickoff_time_uk"].agg(
        lambda x: x.value_counts().head(2).to_dict()).to_dict()
    names = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    t["matches_by_weekday_dev"] = {names[int(k)]: int(v) for k, v in dev.weekday.value_counts().sort_index().items()}
    t["capture_rule_counts_dev"] = dev.pre_odds_capture_rule.value_counts().to_dict()
    t["capture_ambiguous_dev_1920+"] = int(d19.capture_rule_ambiguous.sum())
    t["capture_ambiguous_by_weekday_1920+"] = {names[int(k)]: int(v) for k, v in
                                               d19[d19.capture_rule_ambiguous].weekday.value_counts().sort_index().items()}
    t["capture_time_unverifiable_dev"] = int(dev.capture_time_unverifiable.sum())
    lag = (dev.match_date - dev.pre_odds_capture_date_est).dt.days
    t["days_capture_to_match_dev"] = {int(k): int(v) for k, v in lag.value_counts().sort_index().items()}
    dated = dev.match_date.notna()
    t["invariant_cutoff_le_match_date"] = bool((dev.info_cutoff_date[dated] <= dev.match_date[dated]).all())
    t["rows_without_date_excluded_from_invariant"] = int((~dated).sum())
    # movimiento pre -> cierre (solo cuotas) por día de la semana, 2019/20-2023/24
    b = bench.loc[d19.index]
    rows = []
    for k in range(7):
        m = (d19.weekday == k) & b.A_consensus_valid & b.B_consensus_valid
        mb = (d19.weekday == k) & b.A_b365_valid & b.B_b365_valid
        if m.sum() < 30:
            continue
        same = ((d19.ou_pre_b365_over == d19.ou_close_b365_over) & (d19.ou_pre_b365_under == d19.ou_close_b365_under))[mb]
        rows.append({"weekday": names[k], "days_after_capture": int(lag[d19.index][d19.weekday == k].median()),
                     "n_avg": int(m.sum()), "median_abs_move_avg": round(float((b.p_B_consensus - b.p_A_consensus)[m].abs().median()), 4),
                     "n_b365": int(mb.sum()), "median_abs_move_b365": round(float((b.p_B_b365 - b.p_A_b365)[mb].abs().median()), 4),
                     "pct_b365_pre_equals_close": round(float(same.mean()) * 100, 1)})
    t["pre_to_close_movement_by_weekday_1920_2324"] = rows
    # leakage check benchmark C por fuerza bruta (muestra)
    rng = np.random.default_rng(20261127)
    idx = rng.choice(dev.index[dev.info_cutoff_date.notna()], size=300, replace=False)
    errs = 0
    for i in idx:
        r = dev.loc[i]
        h = dev[(dev["div"] == r["div"]) & (dev.match_date < r.info_cutoff_date) & dev.over25.notna()]
        p = (h.over25.sum() + 1) / (len(h) + 2)
        errs += abs(p - bench.loc[i, "p_C_hist_freq"]) > 1e-12
    t["benchmark_C_bruteforce_mismatches_of_300"] = int(errs)
    return t


# ---------------------------------------------------------------- Pinnacle
def pinnacle_investigation(dev: pd.DataFrame, bench: pd.DataFrame) -> dict:
    p: dict = {}
    d19 = dev.season_code >= "1920"
    rows = []
    for sc in sorted(dev.season_code[d19].unique()):
        m = (dev.season_code == sc)
        for when, tag in (("pre", "A"), ("close", "B")):
            mm = m & bench[f"{tag}_pin_valid"] & bench[f"{tag}_b365_valid"]
            diff = (bench[f"p_{tag}_pin"] - bench[f"p_{tag}_b365"])[mm].abs()
            rows.append({"season": sc, "kind": when, "n": int(mm.sum()), "mean_absdiff": round(float(diff.mean()), 4),
                         "p90_absdiff": round(float(diff.quantile(.9)), 4)})
    p["dev_pin_vs_b365_by_season"] = rows
    # presencia (nivel 0) por mes en reservados
    l0 = pd.concat([holdout.load_level0("holdout"), holdout.load_level0("prospective")])
    l0["month"] = l0.match_date.dt.to_period("M").astype(str)
    pres = l0.groupby("month").agg(n=("match_id", "size"), pin_pre=("has_ou_pre_pin_pair", "mean"),
                                   pin_close=("has_ou_close_pin_pair", "mean"), b365_pre=("has_ou_pre_b365_pair", "mean"),
                                   avg_pre=("has_ou_pre_avg_pair", "mean"), avg_close=("has_ou_close_avg_pair", "mean"))
    p["reserved_presence_by_month_level0"] = (pres * [1, 100, 100, 100, 100, 100]).round(1).reset_index().to_dict("records")
    return p


def benchmark_coverage(dev: pd.DataFrame, bench: pd.DataFrame) -> dict:
    c: dict = {}
    base = (dev.season_code >= "0506") & dev.fthg.notna() & ~dev.duplicate_key
    for name, req in {"A": ["A_consensus"], "A+A_b365": ["A_consensus", "A_b365"],
                      "A+A_b365+A_pin": ["A_consensus", "A_b365", "A_pin"], "A+B": ["A_consensus", "B_consensus"],
                      "A+B+A_b365+B_b365": ["A_consensus", "B_consensus", "A_b365", "B_b365"]}.items():
        c[f"common_sample_{name}"] = int((benchmark.common_sample(bench, req) & base).sum())
    c["A_valid_by_season"] = bench[base].groupby(dev.season_code[base])["A_consensus_valid"].mean().round(4).to_dict()
    c["Astar_n_books_dist_1920+"] = bench[base & (dev.season_code >= "1920")]["Astar_n_books"].value_counts().to_dict()
    c["C_available"] = int(bench.loc[base, "p_C_hist_freq"].notna().sum())
    m = base & bench.A_consensus_valid & bench.A_b365_valid
    c["mean_absdiff_A_vs_A_b365_1920_2324"] = round(float((bench.p_A_consensus - bench.p_A_b365)[m].abs().mean()), 4)
    return c


def generate_all() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    dev = process.load_dev()
    bench = process.load_dev_benchmarks()
    assert (bench["match_id"].values == dev["match_id"].values).all()
    inv, summ = inventory()
    inv.to_csv(OUT / "inventory_by_division_season.csv", index=False)
    summ.to_csv(OUT / "inventory_by_division.csv", index=False)
    q = quality_dev(dev)
    ex = apply_exclusions(dev, bench)
    ex.pop("by_division_season").to_csv(OUT / "market_A_eligibility_by_division_season.csv", index=False)
    t = temporal_diagnostics(dev, bench)
    pin = pinnacle_investigation(dev, bench)
    cov = benchmark_coverage(dev, bench)
    for name, obj in (("quality_dev", q), ("exclusions", ex), ("temporal_diagnostics", t),
                      ("pinnacle_investigation", pin), ("benchmark_coverage", cov)):
        (OUT / f"{name}.json").write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str))
    return {"inventory_rows": len(inv), "exclusions": ex, "temporal": {k: t[k] for k in (
        "invariant_cutoff_le_match_date", "benchmark_C_bruteforce_mismatches_of_300", "capture_ambiguous_dev_1920+")},
            "benchmark_coverage": cov}

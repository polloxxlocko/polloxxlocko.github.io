"""Ejecutor de etapas GATE 2 / GATE 2.1.

Uso:
  python experiments/gate2/run.py <etapa> --out DIR [--clean]
Etapas: poisson_tuning | m3_tuning | inner_base | m4 | evaluate | all | m3_spec_sensitivity
  --out DIR   directorio de la ejecución (obligatorio; experiments/gate2/ publicado es de solo lectura)
  --clean     ejecución limpia: DIR debe ser nuevo o vacío; no se reutiliza ninguna salida previa
Preregistro: MODEL_SPECIFICATION.md §A y configs/gate2.json (desviación D-1: boundary_rule).
Cada ejecución escribe DIR/RUN_MANIFEST.json (commit, hashes de código, configuración y dataset,
versiones, accesos a datos sellados antes/después) y, al terminar, el SHA-256 de cada artefacto."""
import argparse
import datetime as dt
import hashlib
import itertools
import json
import os
import platform
import subprocess
import sys
import time

# Un hilo BLAS por proceso: evita sobresuscripción con 4 procesos y hace el cálculo determinista
# (mismo orden de operaciones de punto flotante en cualquier máquina).
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

from functools import partial  # noqa: E402

from qsports import features, gate2, holdout, models, paths, walkforward  # noqa: E402
from qsports import validation as val  # noqa: E402


def _sel(fam, ids, frame, seas, mask=None, block="tuning"):
    P = gate2.load_preds(fam)
    return gate2.select_best(P[(P.block == block) & P.config_id.isin(ids)], frame, seas, mask_col=mask, order=ids)


def tune(family, grid_key, base_grid, make_spec, run_specs, frame, seas, mask=None):
    """Selección en el bloque de ajuste con la regla de extensión de borde (D-1).
    base_grid: {dim: [valores]}; make_spec(params) -> (cid, params, factory, cols)."""
    rule = gate2.cfg()["boundary_rule"]
    ext = rule["dims"].get(grid_key, {})
    grid = {k: list(v) for k, v in base_grid.items()}
    steps = {k: 0 for k in ext}
    history = []
    while True:
        combos = [dict(zip(grid, vals)) for vals in itertools.product(*grid.values())]
        specs = [make_spec(c) for c in combos]
        run_specs(specs)
        ids = [s[0] for s in specs]
        best, tab = _sel(family, ids, frame, seas, mask=mask)
        bp = dict(next(s[1] for s in specs if s[0] == best))
        history.append({"grid": {k: list(v) for k, v in grid.items()}, "best": best,
                        "table": tab.to_dict("records")})
        changed = False
        for dim, factor in ext.items():
            vals = sorted(grid[dim])
            if len(base_grid[dim]) < 3 or steps[dim] >= rule["max_steps"]:
                continue
            if bp[dim] == vals[-1]:
                grid[dim].append(_round(vals[-1] * factor))
            elif bp[dim] == vals[0]:
                grid[dim].insert(0, _round(vals[0] / factor))
            else:
                continue
            steps[dim] += 1
            changed = True
        if not changed:
            return best, history


def _round(x):
    return int(round(x)) if x >= 10 else round(x, 6)


def _poisson_runner(family):
    def run_specs(specs):
        frame = gate2.base_frame()
        for cid, prm, fac, cols in specs:
            gate2.run_config(family, cid, prm, fac, frame, gate2.cfg()["blocks"]["tuning_seasons_poisson"], "tuning",
                             "division", 1, columns=cols)
    return run_specs


def _poisson_spec(kind, promoted=False, max_hist=1460):
    def mk(p):
        if kind == "M1":
            cid = f"M1__w{p['window_days']}_r{p['ridge']:g}"
            prm = {"window_days": p["window_days"], "ridge": p["ridge"]}
        else:
            cid = f"M2__h{p['half_life_days']}_r{p['ridge']:g}" + ("_pp" if promoted else "")
            prm = {"half_life_days": p["half_life_days"], "ridge": p["ridge"], "max_history_days": max_hist,
                   "promoted_prior": promoted}
        return cid, prm, partial(models.PoissonModel, **prm), ["home_team", "away_team", "fthg", "ftag"]
    return mk


def stage_poisson_tuning():
    c = gate2.cfg()
    frame = gate2.base_frame()
    seas = c["blocks"]["tuning_seasons_poisson"]
    g1, g2 = c["grids"]["M1_poisson_window"], c["grids"]["M2_poisson_decay"]
    best1, h1 = tune("M1", "M1_poisson_window", {"window_days": g1["window_days"], "ridge": g1["ridge"]},
                     _poisson_spec("M1"), _poisson_runner("M1"), frame, seas)
    best2, h2 = tune("M2", "M2_poisson_decay", {"half_life_days": g2["half_life_days"], "ridge": g2["ridge"]},
                     _poisson_spec("M2", max_hist=g2["max_history_days"]), _poisson_runner("M2"), frame, seas)
    reg = gate2._registry()
    p2 = reg[best2]["params"]
    pp_spec = _poisson_spec("M2", promoted=True, max_hist=g2["max_history_days"])(p2)
    _poisson_runner("M2")([pp_spec])
    best2f, tab2f = _sel("M2", [best2, pp_spec[0]], frame, seas)
    P1, P2 = gate2.load_preds("M1"), gate2.load_preds("M2")
    ladder = gate2.paired(frame, P2[(P2.config_id == best2f) & (P2.block == "tuning")],
                          P1[(P1.config_id == best1) & (P1.block == "tuning")], seas, missing="common_sample")
    res = {"M1_selected": best1, "M1_history": h1, "M2_selected_stage1": best2, "M2_history": h2,
           "M2_promoted_candidate": pp_spec[0], "M2_selected": best2f, "M2_stage2_table": tab2f.to_dict("records"),
           "ladder_M2_vs_M1_tuning": ladder, "M2_justified": bool(ladder["delta_logloss"]["hi"] < 0),
           "M2_justified_legacy_active_weeks": bool(ladder["legacy_active_weeks"]["delta_logloss"]["hi"] < 0)}
    gate2.save_result("poisson_tuning", res)
    print(json.dumps({"M1_selected": best1, "M1_grid_final": h1[-1]["grid"], "M2_selected": best2f,
                      "M2_grid_final": h2[-1]["grid"], "ladder": ladder["delta_logloss"], "cat": ladder["category"],
                      "M2_justified": res["M2_justified"]}, indent=1, default=str))


def stage_m3_tuning():
    c = gate2.cfg()
    g = c["grids"]["M3_logistic"]
    seas = c["blocks"]["tuning_seasons_stacked"]
    base = gate2.base_frame()
    frames = {hl: gate2.feature_frame(base, hl) for hl in g["ewm_half_life_matches"]}
    every = c["refit"]["logistic_every_n_captures"]

    def mk(p):
        cid = f"M3__{p['feature_set']}_h{p['ewm_half_life_matches']}_r{p['ridge']:g}"
        cols = features.feature_columns(p["feature_set"])
        return cid, dict(p), partial(models.LogisticFeatureModel, feature_cols=cols, ridge=p["ridge"]), \
            cols + ["p_C_hist_freq", "over25"]

    def run_specs(specs):
        for hl, fr in frames.items():
            sub = [s for s in specs if s[1]["ewm_half_life_matches"] == hl]
            if sub:
                gate2.run_configs_parallel("M3", sub, fr, seas, "tuning", "pooled", every)

    best, hist = tune("M3", "M3_logistic", {"feature_set": g["feature_sets"], "ewm_half_life_matches":
                                            g["ewm_half_life_matches"], "ridge": g["ridge"]}, mk, run_specs, base, seas)
    final_ids = [r["config_id"] for r in hist[-1]["table"]]
    g_ids = [i for i in final_ids if i.split("__")[1].startswith("G_")]
    s_ids = [i for i in final_ids if i not in g_ids]
    best_g, _ = _sel("M3", g_ids, base, seas)
    best_s, _ = _sel("M3", s_ids, base, seas)
    P = gate2.load_preds("M3")
    h1b = gate2.paired(base, P[(P.config_id == best_s) & (P.block == "tuning")],
                       P[(P.config_id == best_g) & (P.block == "tuning")], seas, missing="common_sample")
    res = {"M3_selected": best, "M3_history": hist, "best_goals_only": best_g, "best_with_shots": best_s,
           "H1b_shots_vs_goals_tuning": h1b, "shots_enter_M4_sport": bool(h1b["delta_logloss"]["hi"] < 0),
           "shots_enter_M4_sport_legacy_active_weeks": bool(h1b["legacy_active_weeks"]["delta_logloss"]["hi"] < 0)}
    gate2.save_result("m3_tuning", res)
    print(json.dumps({"M3_selected": best, "grid_final": hist[-1]["grid"], "best_G": best_g, "best_shots": best_s,
                      "H1b": h1b["delta_logloss"], "cat": h1b["category"], "shots_enter": res["shots_enter_M4_sport"]},
                     indent=1, default=str))


def stage_inner_base():
    """Una evaluación por familia ajustada en la prueba interna (M0, M1*, M2*, M3*)."""
    c = gate2.cfg()
    inner, tun = c["blocks"]["inner_test_seasons"], c["blocks"]["tuning_seasons_poisson"]
    base = gate2.base_frame()
    pt, m3 = gate2.load_result("poisson_tuning"), gate2.load_result("m3_tuning")
    reg = gate2._registry()
    for blk, seas in (("tuning", tun), ("inner", inner)):
        gate2.benchmark_preds(base, "p_A_consensus", "M0b_A", "M0b__A", seas, blk)
        gate2.benchmark_preds(base, "p_C_hist_freq", "M0a_C", "M0a__C", seas, blk)
        gate2.run_config("M0a_w730", "M0a__w730", {"window_days": 730}, partial(models.FreqModel, window_days=730),
                         base, seas, blk, "division", 1, columns=["over25"])
    for fam, cid in (("M1", pt["M1_selected"]), ("M2", pt["M2_selected"])):
        prm = reg[cid]["params"]
        gate2.run_config(fam, cid, prm, partial(models.PoissonModel, **prm), base, inner, "inner", "division", 1,
                         columns=["home_team", "away_team", "fthg", "ftag"])
    cid = m3["M3_selected"]
    prm = reg[cid]["params"]
    frame = gate2.feature_frame(base, prm["ewm_half_life_matches"])
    cols = features.feature_columns(prm["feature_set"])
    gate2.run_configs_parallel("M3", [(cid, prm, partial(models.LogisticFeatureModel, feature_cols=cols,
                                                         ridge=prm["ridge"]), cols + ["p_C_hist_freq", "over25"])],
                               frame, inner, "inner", "pooled", c["refit"]["logistic_every_n_captures"], n_jobs=1)
    print("inner_base ok")


def stage_m4():
    c = gate2.cfg()
    tun, inner = c["blocks"]["tuning_seasons_stacked"], c["blocks"]["inner_test_seasons"]
    base = gate2.base_frame()
    pt, m3 = gate2.load_result("poisson_tuning"), gate2.load_result("m3_tuning")
    P2, P3 = gate2.load_preds("M2"), gate2.load_preds("M3")
    inp2 = P2[P2.config_id == pt["M2_selected"]][["match_id", "p_over"]].rename(columns={"p_over": "inp_m2"})
    inp3 = P3[P3.config_id == m3["M3_selected"]][["match_id", "p_over"]].rename(columns={"p_over": "inp_m3"})
    frame = val.merge_one_to_one(val.merge_one_to_one(base, inp2, context="m4:inp_m2"), inp3, context="m4:inp_m3")
    frame.index = base.index
    sport = ["inp_m2"] + (["inp_m3"] if m3["shots_enter_M4_sport"] else [])
    need = ["p_A_consensus", "over25"] + sport
    every = c["refit"]["logistic_every_n_captures"]

    def run_cal(specs):
        gate2.run_configs_parallel("M4cal", specs, frame, tun, "tuning", "pooled", every)

    def mk_cal(p):
        h = p["half_life_days"]
        return (f"M4cal__h{h}", {"half_life_days": h, "require_cols": sport},
                partial(models.MarketModel, sport_cols=[], half_life_days=h, require_cols=sport), need)

    best_cal, hist_cal = tune("M4cal", "M4_cal", {"half_life_days": c["grids"]["M4_cal"]["half_life_days"]},
                              mk_cal, run_cal, base, tun, mask="elig_A")
    h = gate2._registry()[best_cal]["params"]["half_life_days"]

    def mk_sp(p):
        r = p["ridge"]
        return (f"M4sport__h{h}_r{r:g}", {"half_life_days": h, "ridge": r, "sport_cols": sport, "require_cols": sport},
                partial(models.MarketModel, sport_cols=sport, ridge=r, half_life_days=h, require_cols=sport), need)

    def run_sp(specs):
        gate2.run_configs_parallel("M4sport", specs, frame, tun, "tuning", "pooled", every)

    best_sp, hist_sp = tune("M4sport", "M4_sport", {"ridge": c["grids"]["M4_sport"]["ridge"]}, mk_sp, run_sp, base, tun,
                            mask="elig_A")
    reg = gate2._registry()
    for fam, cid in (("M4cal", best_cal), ("M4sport", best_sp)):
        prm = reg[cid]["params"]
        fac = partial(models.MarketModel, sport_cols=prm.get("sport_cols", []), ridge=prm.get("ridge", 100.0),
                      half_life_days=prm["half_life_days"], require_cols=sport)
        gate2.run_configs_parallel(fam, [(cid, prm, fac, need)], frame, inner, "inner", "pooled", every, n_jobs=1)
    res = {"sport_cols": sport, "M4cal_selected": best_cal, "M4cal_history": hist_cal,
           "M4sport_selected": best_sp, "M4sport_history": hist_sp}
    gate2.save_result("m4", res)
    print(json.dumps({"sport_cols": sport, "M4cal": best_cal, "M4sport": best_sp,
                      "M4sport_grid_final": hist_sp[-1]["grid"]}, indent=1, default=str))


def stage_evaluate():
    """Prueba interna (una vez por familia) + diagnósticos M5 + potencia.
    GATE 2.1: universo explícito con cobertura completa exigida; método principal = semanas calendario;
    método publicado de GATE 2 (semanas activas) para comparar; sensibilidad a bloques de 2, 4, 8 y 12 semanas;
    potencia de superioridad frente a equivalencia."""
    import numpy as np
    import pandas as pd
    from qsports import evaluation as ev
    c = gate2.cfg()
    inner = c["blocks"]["inner_test_seasons"]
    bs = c["selection"]["bootstrap"]
    nb, L0, seed, mode = bs["n_boot_inner"], bs["block_weeks"], bs["seed"], bs["week_mode"]
    delta = c["sesoi_nats"]
    base = gate2.base_frame()
    pt, m3, m4 = gate2.load_result("poisson_tuning"), gate2.load_result("m3_tuning"), gate2.load_result("m4")
    sel = {"A": ("M0b_A", "M0b__A"), "C": ("M0a_C", "M0a__C"), "Freq730": ("M0a_w730", "M0a__w730"),
           "M1": ("M1", pt["M1_selected"]), "M2": ("M2", pt["M2_selected"]), "M3": ("M3", m3["M3_selected"]),
           "M4cal": ("M4cal", m4["M4cal_selected"]), "M4sport": ("M4sport", m4["M4sport_selected"])}

    def get(name, block):
        fam, cid = sel[name]
        P = gate2.load_preds(fam)
        return P[(P.config_id == cid) & (P.block == block)][["match_id", "p_over"]]

    U = gate2.universe(base, inner, "elig_A")
    S = U[["match_id", "match_date", "season_code", "over25"]]
    coverage = {}
    for k in sel:
        g = get(k, "inner")
        coverage[k] = val.require_full_coverage(g, U, f"inner:{k}")  # falla si falta alguna predicción
        S = val.merge_one_to_one(S, g.rename(columns={"p_over": k}), context=f"inner:{k}")
    out = {"n_primary": int(len(S)), "seasons": inner, "delta": delta, "selected": {k: v[1] for k, v in sel.items()},
           "universe": {"definition": "temporadas de la prueba interna, resultado conocido, captura estimable, elig_A",
                        "n_inner_rows": int(base.season_code.isin(inner).sum()), "n_universe": int(len(U))},
           "coverage": coverage, "bootstrap": {"week_mode": mode, "block_weeks": L0, "n_boot": nb, "seed": seed}}
    out["describe"] = {k: ev.describe_forecast(S.over25, S[k]) for k in sel}
    pairs = [("M1", "C"), ("M2", "C"), ("M3", "C"), ("M1", "A"), ("M2", "A"), ("M3", "A"), ("M2", "M1"), ("M3", "M2"),
             ("M4cal", "A"), ("M4sport", "A"), ("M4sport", "M4cal"), ("A", "C"), ("Freq730", "C")]
    cmpk = lambda a, b, m=None, **kw: ev.compare(S.over25[m] if m is not None else S.over25,  # noqa: E731
                                                 (S[a][m] if m is not None else S[a]), (S[b][m] if m is not None else S[b]),
                                                 (S.match_date[m] if m is not None else S.match_date), delta, seed=seed, **kw)
    out["comparisons"] = {f"{a}-{b}": cmpk(a, b, n_boot=nb, block=L0, week_mode=mode) for a, b in pairs}
    out["comparisons_gate2_method_active_weeks"] = {
        f"{a}-{b}": {k: v for k, v in cmpk(a, b, n_boot=nb, block=L0, week_mode="active").items()
                     if k in ("delta_logloss", "category", "dm")} for a, b in pairs}
    sens = {}
    for a, b in pairs:
        rows = []
        for wm in ("calendar", "active"):
            for Lb in bs["sensitivity_block_weeks"]:
                r = cmpk(a, b, n_boot=nb, block=Lb, week_mode=wm)
                rows.append({"week_mode": wm, "block_weeks": Lb, "lo": r["delta_logloss"]["lo"],
                             "hi": r["delta_logloss"]["hi"], "se_boot": r["delta_logloss"]["se_boot"],
                             "category": r["category"]})
        dd = ev.log_loss(S.over25, S[a]) - ev.log_loss(S.over25, S[b])
        wk = ev.week_ids(S.match_date)
        sens[f"{a}-{b}"] = {"mean": out["comparisons"][f"{a}-{b}"]["delta_logloss"]["mean"], "rows": rows,
                            "categories": sorted({r["category"] for r in rows}),
                            "weekly_autocorr_calendar_lags1_8": ev.weekly_autocorrelation(dd, wk, 8, "calendar"),
                            "weekly_autocorr_active_lags1_8": ev.weekly_autocorrelation(dd, wk, 8, "active")}
    out["block_sensitivity"] = sens
    out["per_season"] = {f"{a}-{b}": {sc: float((ev.log_loss(g.over25, g[a]) - ev.log_loss(g.over25, g[b])).mean())
                                      for sc, g in S.groupby("season_code")}
                         for a, b in [("M2", "A"), ("M4cal", "A"), ("M4sport", "M4cal"), ("M2", "M1"), ("M3", "M2")]}
    reg = {"betbrain_1415_1819": (S.season_code <= "1819").to_numpy(), "oddsportal_1920_2122": (S.season_code >= "1920").to_numpy()}
    out["by_regime"] = {}
    for r, m in reg.items():
        out["by_regime"][r] = {}
        for a, b in [("M4sport", "M4cal"), ("M4cal", "A"), ("M2", "A")]:
            cr = cmpk(a, b, m, n_boot=2000, block=L0, week_mode=mode)
            out["by_regime"][r][f"{a}-{b}"] = dict(cr["delta_logloss"], category=cr["category"])
    out["reliability"] = {k: ev.reliability_table(S.over25, S[k]).to_dict("records") for k in ("A", "M2", "M4cal", "M4sport")}
    # diagnósticos M5 (bloque de ajuste, M2*). Bootstrap por clusters de semana (sin cambios respecto de GATE 2).
    P2 = gate2.load_preds("M2")
    d2 = val.merge_one_to_one(P2[(P2.config_id == pt["M2_selected"]) & (P2.block == "tuning")],
                              base[["match_id", "match_date", "fthg", "ftag"]], how="left", context="M5")
    d2 = d2.dropna(subset=["lam_h", "fthg"])  # filas sin λ (sin historial) o sin resultado: fuera del diagnóstico
    lt, yt = d2.lam_h + d2.lam_a, d2.fthg + d2.ftag
    w = ev.week_ids(d2.match_date)
    rng = np.random.default_rng(seed)
    wk = pd.DataFrame({"w": w, "n": (yt - lt) ** 2, "d": lt}).groupby("w")[["n", "d"]].sum().to_numpy()
    reps = []
    for _ in range(2000):
        s_ = wk[rng.integers(0, len(wk), len(wk))]
        reps.append(s_[:, 0].sum() / s_[:, 1].sum())
    rh, ra = (d2.fthg - d2.lam_h).to_numpy(), (d2.ftag - d2.lam_a).to_numpy()
    corr = float(np.corrcoef(rh, ra)[0, 1])
    groups = pd.Series(np.arange(len(d2))).groupby(w).apply(np.array).tolist()
    creps = []
    for _ in range(1000):
        pick = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        creps.append(np.corrcoef(rh[pick], ra[pick])[0, 1])
    disp = float(((yt - lt) ** 2).sum() / lt.sum())
    lo_d, hi_d = np.quantile(reps, [.025, .975])
    lo_c, hi_c = np.quantile(creps, [.025, .975])
    out["M5_diagnostics"] = {"dispersion_index": disp, "dispersion_ci95": [float(lo_d), float(hi_d)],
                             "residual_corr_home_away": corr, "corr_ci95": [float(lo_c), float(hi_c)],
                             "NB_justified": bool(disp > 1.10 and lo_d > 1.05),
                             "bivariate_justified": bool(abs(corr) > 0.05 and (lo_c > 0 or hi_c < 0)), "n": int(len(d2))}
    # potencia: conteo de NIVEL 0 del holdout (metadatos permitidos; sin cuotas ni resultados)
    try:
        l0 = holdout.load_level0("holdout")
        n_h = int((l0.has_ou_pre_avg_pair & l0.ou_pre_avg_overround_in_range & ~l0.capture_rule_ambiguous
                   & l0.has_result & ~l0.duplicate_key).sum())
    except Exception as e:  # auditoría sin datos sellados
        n_h = None
        out["power_note"] = f"nivel 0 del holdout no disponible: {e}"
    out["power"] = {"n_holdout_eligible_level0": n_h,
                    "method": ("se_holdout = se_bootstrap_desarrollo · sqrt(n_desarrollo / n_holdout) (semanas "
                               "calendario, bloque 4); aproximación normal. Superioridad y equivalencia por separado.")}
    for k in ("M4sport-A", "M4sport-M4cal", "M2-A", "M4cal-A"):
        cmp_ = out["comparisons"][k]
        rec = {"sd_delta": cmp_["sd_delta"], "deff_week": cmp_["deff_week"], "se_dev": cmp_["delta_logloss"]["se_boot"],
               "mde_holdout_gate2_formula": ev.mde(cmp_["sd_delta"], n_h, cmp_["deff_week"]) if n_h else None}
        if n_h:
            se_h = cmp_["delta_logloss"]["se_boot"] * (cmp_["n"] / n_h) ** 0.5
            rec["profile_holdout"] = ev.power_profile(se_h, delta)
        out["power"][k] = rec
    # sensibilidad de las decisiones de la escalera (bloque de ajuste) a la definición de semana y al bloque
    lad = {}
    seas_p, seas_s = c["blocks"]["tuning_seasons_poisson"], c["blocks"]["tuning_seasons_stacked"]
    P1, P3 = gate2.load_preds("M1"), gate2.load_preds("M3")
    pairs_t = {"M2_vs_M1": (P2[(P2.config_id == pt["M2_selected"]) & (P2.block == "tuning")],
                            P1[(P1.config_id == pt["M1_selected"]) & (P1.block == "tuning")], seas_p),
               "H1b_shots_vs_goals": (P3[(P3.config_id == m3["best_with_shots"]) & (P3.block == "tuning")],
                                      P3[(P3.config_id == m3["best_goals_only"]) & (P3.block == "tuning")], seas_s)}
    for name, (pa, pb, seas_) in pairs_t.items():
        rows = []
        for Lb in bs["sensitivity_block_weeks"]:
            r = gate2.paired(base, pa, pb, seas_, missing="common_sample", n_boot=bs["n_boot_tuning"], block=Lb)
            for wm, rr in (("calendar", r), ("active", r["legacy_active_weeks"])):
                rows.append({"week_mode": wm, "block_weeks": Lb, "lo": rr["delta_logloss"]["lo"],
                             "hi": rr["delta_logloss"]["hi"], "category": rr["category"],
                             "decision_hi_lt_0": bool(rr["delta_logloss"]["hi"] < 0)})
        lad[name] = {"rows": rows, "decision_stable": len({r["decision_hi_lt_0"] for r in rows}) == 1}
    out["ladder_decision_sensitivity"] = lad
    gate2.save_result("evaluate", out)
    print(json.dumps({"n": out["n_primary"], **{k: (round(v["delta_logloss"]["mean"], 5), round(v["delta_logloss"]["lo"], 5),
                      round(v["delta_logloss"]["hi"], 5), v["category"]) for k, v in out["comparisons"].items()},
                      "M5": out["M5_diagnostics"], "power_n": n_h}, indent=1, default=str))


def stage_m3_spec_sensitivity():
    """GATE 2.1 (exigencia 6): el preregistro de M3 dice log(1 + partidos previos); GATE 2 usó el conteo
    lineal estandarizado. Se repite la grilla FINAL de M3 en el BLOQUE DE AJUSTE con log1p (sin tocar la prueba
    interna) y se comprueba si cambian la selección de M3 y la decisión H1b (tiros en M4-sport)."""
    c = gate2.cfg()
    seas = c["blocks"]["tuning_seasons_stacked"]
    base = gate2.base_frame()
    m3 = gate2.load_result("m3_tuning")
    every = c["refit"]["logistic_every_n_captures"]
    final_ids = [r["config_id"] for r in m3["M3_history"][-1]["table"]]
    reg = gate2._registry()
    specs_by_hl = {}
    for cid in final_ids:
        prm = dict(reg[cid]["params"])
        cols = features.feature_columns(prm["feature_set"], n_prior="log1p")
        new = cid.replace("M3__", "M3log__")
        specs_by_hl.setdefault(prm["ewm_half_life_matches"], []).append(
            (new, {**prm, "n_prior": "log1p"}, partial(models.LogisticFeatureModel, feature_cols=cols, ridge=prm["ridge"]),
             cols + ["p_C_hist_freq", "over25"]))
    for hl, specs in specs_by_hl.items():
        gate2.run_configs_parallel("M3log", specs, gate2.feature_frame(base, hl), seas, "tuning", "pooled", every)
    ids = [s[0] for v in specs_by_hl.values() for s in v]
    P = gate2.load_preds("M3log")
    best, tab = gate2.select_best(P[(P.block == "tuning") & P.config_id.isin(ids)], base, seas, order=ids)
    g_ids = [i for i in ids if i.split("__")[1].startswith("G_")]
    s_ids = [i for i in ids if i not in g_ids]
    best_g, _ = gate2.select_best(P[(P.block == "tuning") & P.config_id.isin(g_ids)], base, seas, order=g_ids)
    best_s, _ = gate2.select_best(P[(P.block == "tuning") & P.config_id.isin(s_ids)], base, seas, order=s_ids)
    h1b = gate2.paired(base, P[(P.config_id == best_s) & (P.block == "tuning")],
                       P[(P.config_id == best_g) & (P.block == "tuning")], seas, missing="common_sample")
    P3 = gate2.load_preds("M3")
    lin_vs_log = gate2.paired(base, P[(P.config_id == m3["M3_selected"].replace("M3__", "M3log__")) & (P.block == "tuning")],
                              P3[(P3.config_id == m3["M3_selected"]) & (P3.block == "tuning")], seas,
                              missing="common_sample")
    res = {"note": "solo bloque de ajuste; la prueba interna no se reevalúa", "M3log_selected": best,
           "M3log_table": tab.to_dict("records"), "M3_selected_linear": m3["M3_selected"],
           "same_selection_up_to_transform": best.replace("M3log__", "M3__") == m3["M3_selected"],
           "best_goals_only": best_g, "best_with_shots": best_s, "H1b_log1p": h1b,
           "shots_enter_M4_sport_log1p": bool(h1b["delta_logloss"]["hi"] < 0),
           "shots_enter_M4_sport_linear": m3["shots_enter_M4_sport"],
           "H1b_decision_unchanged": bool(h1b["delta_logloss"]["hi"] < 0) == m3["shots_enter_M4_sport"],
           "selected_log1p_minus_linear_tuning": lin_vs_log}
    gate2.save_result("m3_spec_sensitivity", res)
    print(json.dumps({k: v for k, v in res.items() if k not in ("M3log_table", "H1b_log1p", "selected_log1p_minus_linear_tuning")},
                     indent=1, default=str))
    print("H1b log1p:", h1b["delta_logloss"], h1b["category"])
    print("log1p - lineal (M3*):", lin_vs_log["delta_logloss"], lin_vs_log["category"])


STAGES = {"poisson_tuning": stage_poisson_tuning, "m3_tuning": stage_m3_tuning, "inner_base": stage_inner_base,
          "m4": stage_m4, "evaluate": stage_evaluate}
EXTRA_STAGES = {"m3_spec_sensitivity": stage_m3_spec_sensitivity}


# ---------------------------------------------------------------- manifiesto de la ejecución
def _git(*args):
    r = subprocess.run(["git", *args], cwd=paths.ROOT, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def _sealed_snapshot():
    return {"access_log_entries": {p: holdout.seal_state(p)["access_log_entries"] for p in ("holdout", "reserve")},
            "fence_log": walkforward.fence_log_summary()}


def _versions():
    import numpy, pandas, pyarrow, scipy  # noqa: E401
    return {"python": sys.version.split()[0], "platform": platform.platform(), "numpy": numpy.__version__,
            "pandas": pandas.__version__, "scipy": scipy.__version__, "pyarrow": pyarrow.__version__}


def manifest_start(out, stages, clean):
    m = {"started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "stages": stages, "clean": clean,
         "git_commit": _git("rev-parse", "HEAD"), "git_dirty": bool(_git("status", "--porcelain")),
         "code_files_sha256": gate2.code_files(), "code_hash": gate2.code_hash(),
         "dataset": gate2.dataset_hashes(), "versions": _versions(),
         "threads_env": {v: os.environ.get(v) for v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
         "sealed_before": _sealed_snapshot(),
         "fence": {"fence_max_eval_season": gate2.cfg()["blocks"]["fence_max_eval_season"],
                   "evaluated_blocks": {k: gate2.cfg()["blocks"][k] for k in
                                        ("tuning_seasons_poisson", "tuning_seasons_stacked", "inner_test_seasons")}},
         "reads_published_outputs": False}
    (out / "RUN_MANIFEST.json").write_text(json.dumps(m, indent=1, ensure_ascii=False, default=str))
    return m


def manifest_end(out, m, t0):
    arts = {}
    for f in sorted(out.rglob("*")):
        if f.is_file() and f.name != "RUN_MANIFEST.json" and not f.name.endswith(".tmp"):
            arts[str(f.relative_to(out))] = gate2.sha256_file(f)
    m.update(finished_utc=dt.datetime.now(dt.timezone.utc).isoformat(), wall_s=round(time.time() - t0, 1),
             sealed_after=_sealed_snapshot(), artifacts_sha256=arts,
             artifacts_set_sha256=hashlib.sha256(json.dumps(arts, sort_keys=True).encode()).hexdigest())
    m["sealed_unchanged"] = m["sealed_before"] == m["sealed_after"]
    (out / "RUN_MANIFEST.json").write_text(json.dumps(m, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=[*STAGES, "all", *EXTRA_STAGES])
    ap.add_argument("--out", required=True)
    ap.add_argument("--clean", action="store_true")
    a = ap.parse_args()
    out = gate2.configure(a.out, "clean" if a.clean else "resume")
    stages = list(STAGES) if a.stage == "all" else [a.stage]
    if a.clean and _git("status", "--porcelain"):
        sys.exit("Ejecución limpia: el árbol de trabajo tiene cambios sin commit (el código debe ser un commit exacto).")
    t0 = time.time()
    man = manifest_start(out, stages, a.clean) if not (out / "RUN_MANIFEST.json").exists() else \
        json.loads((out / "RUN_MANIFEST.json").read_text())
    if man.get("code_hash") != gate2.code_hash():
        sys.exit("El código cambió respecto del manifiesto de esta ejecución: use un directorio nuevo.")
    for s_ in stages:
        print(f"== etapa {s_}", flush=True)
        (STAGES | EXTRA_STAGES)[s_]()
    man.setdefault("stages_done", []).extend(stages)
    manifest_end(out, man, t0)
    print(f"== fin {time.time() - t0:.0f}s")

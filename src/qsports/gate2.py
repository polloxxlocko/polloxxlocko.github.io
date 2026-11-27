"""Orquestación de los experimentos de GATE 2 (preregistro: MODEL_SPECIFICATION.md §A, configs/gate2.json).

Cada etapa:
- guarda TODAS las predicciones fuera de muestra (también de configuraciones descartadas) en
  experiments/gate2/predictions/<familia>.parquet;
- guarda los registros de ajuste (tiempo, iteraciones, convergencia, parámetros) en
  experiments/gate2/fitlogs/<familia>.parquet;
- registra tiempo de pared, CPU del proceso principal, suma de tiempos de ajuste (trabajadores)
  y memoria máxima en experiments/gate2/runlog.json;
- es reanudable: si la salida de una configuración existe, no se recalcula.
"""
from __future__ import annotations

import json
import resource
import time
from functools import partial
from pathlib import Path

import numpy as np
import pandas as pd

from . import evaluation as ev
from . import features, models, paths, process, walkforward as wf
from .ou import p_over25_poisson

OUT = paths.ROOT / "experiments" / "gate2"
N_JOBS = 4


class SelectionLeakError(RuntimeError):
    """La selección recibió datos fuera del bloque de ajuste."""


def cfg() -> dict:
    return wf.gate2_config()


# ---------------------------------------------------------------- datos
def base_frame() -> pd.DataFrame:
    dev = process.load_dev()
    b = process.load_dev_benchmarks()
    assert (dev["match_id"].values == b["match_id"].values).all()
    for c in ["p_A_consensus", "A_consensus_valid", "p_C_hist_freq"]:
        dev[c] = b[c].values
    dev["elig_A"] = (dev["A_consensus_valid"].astype(bool) & ~dev["capture_rule_ambiguous"].astype(bool)
                     & dev["fthg"].notna() & ~dev["duplicate_key"].astype(bool))
    return dev


def feature_frame(base: pd.DataFrame, hl: float) -> pd.DataFrame:
    cache = paths.FEATURES_DEV / f"team_ewm_hl{int(hl)}.parquet"
    if cache.exists():
        f = pd.read_parquet(cache)
        assert (f["match_id"].values == base["match_id"].values).all()
        f = f.drop(columns=["match_id"])
    else:
        f = features.build_features(base, hl)
        f.assign(match_id=base["match_id"].values).to_parquet(cache, index=False)
    return pd.concat([base, f.set_index(base.index)], axis=1)


# ---------------------------------------------------------------- persistencia
def _paths(family):
    """Predicciones: un archivo por configuración en predictions/<familia>/<config_id>.parquet
    (p_over en float64 exacto; λ auxiliares en float32). Registros de ajuste: fitlogs/<familia>.parquet."""
    d = OUT / "predictions" / family
    d.mkdir(parents=True, exist_ok=True)
    (OUT / "fitlogs").mkdir(parents=True, exist_ok=True)
    return d, OUT / "fitlogs" / f"{family}.parquet"


def load_preds(family) -> pd.DataFrame:
    d, _ = _paths(family)
    files = sorted(d.glob("*.parquet"))
    if not files:
        return pd.DataFrame(columns=["match_id", "config_id", "block"])
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def _append(family, preds, logs):
    d, lp = _paths(family)
    preds = preds.drop(columns=[c for c in ("train_max_date", "n_train") if c in preds.columns])  # están en fitlogs
    for c in ("lam_h", "lam_a"):
        if c in preds.columns:
            preds[c] = preds[c].astype("float32")
    for cid, g in preds.groupby("config_id", sort=False):
        f = d / f"{cid}.parquet"
        out = pd.concat([pd.read_parquet(f), g], ignore_index=True) if f.exists() else g
        out.to_parquet(f, index=False, compression="zstd")
    old = pd.read_parquet(lp) if lp.exists() else None
    out = pd.concat([old, logs], ignore_index=True) if old is not None else logs
    out.to_parquet(lp, index=False, compression="zstd")


def _registry() -> dict:
    p = OUT / "configs.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _save_registry(r):
    (OUT / "configs.json").write_text(json.dumps(r, indent=1, ensure_ascii=False, default=str))


def _runlog(stage, rec):
    p = OUT / "runlog.json"
    r = json.loads(p.read_text()) if p.exists() else {}
    r.setdefault(stage, []).append(rec)
    p.write_text(json.dumps(r, indent=1, ensure_ascii=False, default=str))


def run_config(family, config_id, params, factory, frame, seasons, block, scope, every, columns=None):
    """Ejecuta (o reutiliza) una configuración y guarda predicciones, fitlogs y consumo."""
    have = load_preds(family)
    if len(have) and ((have["config_id"] == config_id) & (have["block"] == block)).any():
        return have[(have["config_id"] == config_id) & (have["block"] == block)]
    t0, c0 = time.perf_counter(), resource.getrusage(resource.RUSAGE_SELF)
    preds, logs = wf.run(frame, factory, seasons, scope=scope, refit_every=every, label=config_id,
                         n_jobs=N_JOBS if scope == "division" else 1, columns=columns)
    c1 = resource.getrusage(resource.RUSAGE_SELF)
    preds["config_id"], preds["block"] = config_id, block
    logs["config_id"], logs["block"] = config_id, block
    _append(family, preds, logs)
    reg = _registry()
    reg.setdefault(config_id, {"family": family, "params": params, "blocks": []})
    reg[config_id]["blocks"] = sorted(set(reg[config_id]["blocks"]) | {block})
    _save_registry(reg)
    _runlog(family, {"config_id": config_id, "block": block, "wall_s": round(time.perf_counter() - t0, 2),
                     "cpu_main_s": round((c1.ru_utime + c1.ru_stime) - (c0.ru_utime + c0.ru_stime), 2),
                     "sum_fit_s": round(float(logs["wall_ms"].sum()) / 1000, 2) if len(logs) else 0.0,
                     "max_rss_main_mb": round(c1.ru_maxrss / 1024, 1), "n_fits": int(len(logs)),
                     "n_nonconverged": int((~logs["converged"]).sum()) if len(logs) else 0,
                     "n_preds": int(len(preds)), "n_nan_preds": int(preds["p_over"].isna().sum())})
    return preds


# ---------------------------------------------------------------- selección (solo bloque de ajuste)
def assert_block(pred: pd.DataFrame, frame: pd.DataFrame, allowed) -> None:
    seasons = pred["match_id"].map(frame.set_index("match_id")["season_code"])
    bad = sorted(set(seasons.dropna()) - set(allowed))
    if bad or seasons.isna().any():
        raise SelectionLeakError(f"La selección recibió temporadas fuera del bloque de ajuste: {bad}")


def select_best(pred: pd.DataFrame, frame: pd.DataFrame, allowed, mask_col: str | None = None,
                order: list[str] | None = None) -> tuple[str, pd.DataFrame]:
    """Mejor configuración por log loss medio sobre la muestra común; empate -> primera en `order`."""
    assert_block(pred, frame, allowed)
    y = frame.set_index("match_id")
    wide = pred.pivot_table(index="match_id", columns="config_id", values="p_over")
    ok = wide.notna().all(axis=1) & y.loc[wide.index, "over25"].notna().values
    if mask_col:
        ok &= y.loc[wide.index, mask_col].astype(bool).values
    wide = wide[ok]
    yy = y.loc[wide.index, "over25"].to_numpy()
    tab = pd.DataFrame({"config_id": wide.columns,
                        "logloss": [ev.log_loss(yy, wide[c].to_numpy()).mean() for c in wide.columns],
                        "n": len(wide)}).sort_values("logloss", kind="mergesort")
    best = tab["logloss"].min()
    cands = tab[tab["logloss"] == best]["config_id"].tolist()
    if order:
        cands.sort(key=lambda c: order.index(c) if c in order else 10 ** 6)
    return cands[0], tab


def paired(frame, pa: pd.DataFrame, pb: pd.DataFrame, mask_col=None, n_boot=2000, delta=None):
    """Comparación pareada (a − b) sobre filas comunes con resultado."""
    m = (frame[["match_id", "match_date", "over25"] + ([mask_col] if mask_col else [])]
         .merge(pa[["match_id", "p_over"]].rename(columns={"p_over": "a"}), on="match_id")
         .merge(pb[["match_id", "p_over"]].rename(columns={"p_over": "b"}), on="match_id"))
    m = m.dropna(subset=["over25", "a", "b"])
    if mask_col:
        m = m[m[mask_col].astype(bool)]
    return ev.compare(m["over25"], m["a"], m["b"], m["match_date"], delta=delta or cfg()["sesoi_nats"],
                      n_boot=n_boot, seed=cfg()["selection"]["bootstrap"]["seed"])


# ---------------------------------------------------------------- etapas
def grid_m1(frame):
    g = cfg()["grids"]["M1_poisson_window"]
    seas = cfg()["blocks"]["tuning_seasons_poisson"]
    ids = []
    for wdays in g["window_days"]:
        for r in g["ridge"]:
            cid = f"M1__w{wdays}_r{r:g}"
            ids.append(cid)
            run_config("M1", cid, {"window_days": wdays, "ridge": r},
                       partial(models.PoissonModel, window_days=wdays, ridge=r), frame, seas, "tuning",
                       "division", 1, columns=["home_team", "away_team", "fthg", "ftag"])
    return ids


def grid_m2(frame, promoted=False, only=None):
    g = cfg()["grids"]["M2_poisson_decay"]
    seas = cfg()["blocks"]["tuning_seasons_poisson"]
    ids = []
    combos = [(h, r) for h in g["half_life_days"] for r in g["ridge"]] if only is None else [only]
    for h, r in combos:
        cid = f"M2__h{h}_r{r:g}" + ("_pp" if promoted else "")
        ids.append(cid)
        run_config("M2", cid, {"half_life_days": h, "ridge": r, "max_history_days": g["max_history_days"],
                               "promoted_prior": promoted},
                   partial(models.PoissonModel, half_life_days=h, ridge=r, max_history_days=g["max_history_days"],
                           promoted_prior=promoted), frame, seas, "tuning", "division", 1,
                   columns=["home_team", "away_team", "fthg", "ftag"])
    return ids


def lambda_from_p(p):
    """Inversa numérica de P(Over 2,5 | λ) (monótona) — para diagnósticos cuando falta λ."""
    lo, hi = np.full_like(p, 1e-6), np.full_like(p, 15.0)
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        f = p_over25_poisson(mid)
        lo, hi = np.where(f < p, mid, lo), np.where(f < p, hi, mid)
    return 0.5 * (lo + hi)


def save_result(stage: str, res: dict) -> None:
    p = OUT / "results.json"
    r = json.loads(p.read_text()) if p.exists() else {}
    r[stage] = res
    p.write_text(json.dumps(r, indent=1, ensure_ascii=False, default=float))


def load_result(stage: str) -> dict:
    return json.loads((OUT / "results.json").read_text())[stage]


# ---------------------------------------------------------------- grillas en paralelo por configuración
_W: dict = {}


def _winit(frame, seasons, scope, every):
    _W.update(frame=frame, seasons=seasons, scope=scope, every=every)


def _wjob(spec):
    cid, factory, columns = spec
    t0 = time.perf_counter()
    preds, logs = wf.run(_W["frame"], factory, _W["seasons"], scope=_W["scope"], refit_every=_W["every"],
                         label=cid, n_jobs=1, columns=columns)
    return cid, preds, logs, time.perf_counter() - t0


def run_configs_parallel(family, specs, frame, seasons, block, scope, every, n_jobs=N_JOBS):
    """specs: lista de (config_id, params, factory, columns). Calcula en paralelo y escribe en serie."""
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor
    have = load_preds(family)
    done = set(have.loc[have["block"] == block, "config_id"]) if len(have) else set()
    todo = [s for s in specs if s[0] not in done]
    if not todo:
        return
    cols = sorted({c for s in todo for c in (s[3] or [])})
    base = ["match_id", "div", "season_code", "match_date", "pre_odds_capture_date_est"]
    sub = frame[list(dict.fromkeys(base + cols))]
    params = {s[0]: s[1] for s in todo}
    ctx = mp.get_context("forkserver")
    with ProcessPoolExecutor(min(n_jobs, len(todo)), mp_context=ctx, initializer=_winit,
                             initargs=(sub, list(seasons), scope, every)) as ex:
        for cid, preds, logs, wall in ex.map(_wjob, [(s[0], s[2], s[3]) for s in todo]):
            preds["config_id"], preds["block"] = cid, block
            logs["config_id"], logs["block"] = cid, block
            _append(family, preds, logs)
            reg = _registry()
            reg.setdefault(cid, {"family": family, "params": params[cid], "blocks": []})
            reg[cid]["blocks"] = sorted(set(reg[cid]["blocks"]) | {block})
            _save_registry(reg)
            _runlog(family, {"config_id": cid, "block": block, "wall_s": round(wall, 2), "cpu_main_s": None,
                             "sum_fit_s": round(float(logs["wall_ms"].sum()) / 1000, 2),
                             "max_rss_main_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
                             "n_fits": int(len(logs)), "n_nonconverged": int((~logs["converged"]).sum()),
                             "n_preds": int(len(preds)), "n_nan_preds": int(preds["p_over"].isna().sum()),
                             "parallel_config_level": True})


def benchmark_preds(frame, col, family, cid, seasons, block):
    """Guarda un benchmark (A o C) como 'predicciones' de su familia para la auditoría."""
    have = load_preds(family)
    if len(have) and ((have["config_id"] == cid) & (have["block"] == block)).any():
        return
    r = frame[frame["season_code"].isin(seasons)]
    p = pd.DataFrame({"match_id": r["match_id"].values, "p_over": r[col].values,
                      "fit_tau": r["pre_odds_capture_date_est"].values, "config_id": cid, "block": block})
    _append(family, p, pd.DataFrame({"config_id": [cid], "block": [block], "converged": [True], "wall_ms": [0.0]}))
    reg = _registry()
    reg.setdefault(cid, {"family": family, "params": {"source": col}, "blocks": []})
    reg[cid]["blocks"] = sorted(set(reg[cid]["blocks"]) | {block})
    _save_registry(reg)

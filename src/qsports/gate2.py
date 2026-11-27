"""Orquestación de los experimentos de GATE 2 (preregistro: MODEL_SPECIFICATION.md §A, configs/gate2.json).

GATE 2.1 (exigencia 1: reproducibilidad real):
- Cada ejecución escribe en un directorio propio (`configure(out_dir, mode)`). El directorio
  publicado `experiments/gate2/` es de SOLO LECTURA para el pipeline.
- `mode="clean"`: el directorio debe ser nuevo o estar vacío; no se lee ninguna predicción,
  variable ni resultado previo (tampoco la caché de variables de data/features/dev).
- Una salida (predicciones de una configuración en un bloque, o variables EWMA) solo se
  reutiliza si existe su MANIFIESTO DE COMPLETITUD con la misma clave de caché
  (hash del código + parámetros + temporadas + contenido exacto de las columnas de entrada) y el
  SHA-256 del archivo coincide. La mera existencia de predicciones no es evidencia de una
  ejecución completa: sin manifiesto válido, se recalcula.
- Escrituras atómicas (archivo temporal + os.replace); nunca se concatena sobre un archivo previo.
- Predicciones: predictions/<familia>/<config_id>__<bloque>.parquet (+ .json de completitud).
  Registros de ajuste: fitlogs/<familia>/<config_id>__<bloque>.parquet (incluyen
  `train_max_date` y `n_train` de cada ajuste; las predicciones se enlazan por
  (config_id, bloque, scope, fit_tau)).
- Comparaciones sobre un universo explícito con validación de entradas (qsports.validation).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import resource
import time
from functools import partial  # noqa: F401  (re-exportado para run.py)
from pathlib import Path

import numpy as np
import pandas as pd

from . import evaluation as ev
from . import features, holdout, models, paths, process, validation as val, walkforward as wf
from .ou import p_over25_poisson

PUBLISHED = paths.ROOT / "experiments" / "gate2"
OUT = PUBLISHED  # directorio activo (lo cambia configure); por defecto solo lectura
N_JOBS = 4
_RUN: dict = {"mode": "read_only", "features": paths.FEATURES_DEV}

CODE_FILES_GLOBS = ("src/qsports/*.py", "experiments/gate2/run.py", "configs/*.json", "requirements-lock.txt",
                    "pyproject.toml")


class SelectionLeakError(RuntimeError):
    """La selección recibió datos fuera del bloque de ajuste."""


class ReadOnlyError(RuntimeError):
    """Intento de escribir en el directorio publicado de GATE 2."""


def cfg() -> dict:
    return wf.gate2_config()


# ---------------------------------------------------------------- directorio de ejecución
def configure(out_dir, mode: str = "resume") -> Path:
    """Fija el directorio de salida. mode='clean': debe ser nuevo o vacío; 'resume': reutiliza solo
    salidas con manifiesto válido."""
    global OUT
    out_dir = Path(out_dir).resolve()
    if out_dir == PUBLISHED.resolve():
        raise ReadOnlyError("experiments/gate2/ contiene los resultados publicados de GATE 2 y es de solo lectura.")
    if mode not in ("clean", "resume"):
        raise ValueError(mode)
    if mode == "clean" and out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"Modo limpio: {out_dir} no está vacío.")
    out_dir.mkdir(parents=True, exist_ok=True)
    OUT = out_dir
    _RUN.update(mode=mode, features=out_dir / "features")
    return out_dir


def _reusable() -> bool:
    """Reutilizar salidas con manifiesto válido. En modo 'clean' el directorio empezó vacío, así que toda salida
    válida que contenga la produjo ESTA ejecución (p. ej., configuraciones repetidas al extender la grilla)."""
    return _RUN["mode"] in ("clean", "resume")


def _writable() -> None:
    if _RUN["mode"] == "read_only" or OUT.resolve() == PUBLISHED.resolve():
        raise ReadOnlyError("Configure un directorio de ejecución (gate2.configure) antes de escribir.")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def code_files() -> dict[str, str]:
    files = sorted({p for g in CODE_FILES_GLOBS for p in paths.ROOT.glob(g) if p.is_file()})
    return {str(p.relative_to(paths.ROOT)): sha256_file(p) for p in files}


_CODE_HASH: dict = {}


def code_hash() -> str:
    if "h" not in _CODE_HASH:
        _CODE_HASH["h"] = hashlib.sha256(json.dumps(code_files(), sort_keys=True).encode()).hexdigest()
    return _CODE_HASH["h"]


def frame_hash(df: pd.DataFrame) -> str:
    """Hash del contenido exacto (valores, tipos y orden de columnas) de un DataFrame."""
    h = hashlib.sha256()
    h.update(json.dumps([str(c) for c in df.columns]).encode())
    h.update(json.dumps([str(t) for t in df.dtypes]).encode())
    h.update(pd.util.hash_pandas_object(df, index=False).to_numpy().tobytes())
    return h.hexdigest()


def _key(**parts) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


def _atomic_parquet(df: pd.DataFrame, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    df.to_parquet(tmp, index=False, compression="zstd")
    os.replace(tmp, path)
    return sha256_file(path)


def _atomic_json(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str))
    os.replace(tmp, path)


# ---------------------------------------------------------------- datos
def base_frame() -> pd.DataFrame:
    dev = process.load_dev()
    b = process.load_dev_benchmarks()
    val.unique_ids(dev, "match_id", "dev")
    if not (dev["match_id"].values == b["match_id"].values).all():
        raise val.InputValidationError("benchmarks desalineados con el conjunto de desarrollo")
    for c in ["p_A_consensus", "A_consensus_valid", "p_C_hist_freq"]:
        dev[c] = b[c].values
    dev["elig_A"] = (dev["A_consensus_valid"].astype(bool) & ~dev["capture_rule_ambiguous"].astype(bool)
                     & dev["fthg"].notna() & ~dev["duplicate_key"].astype(bool))
    return dev


def dataset_hashes() -> dict:
    dev, b = process.load_dev(), process.load_dev_benchmarks()
    return {"dev_matches_content_sha256": holdout.content_hash(dev),
            "dev_benchmarks_content_sha256": holdout.content_hash(b), "n_dev_rows": int(len(dev))}


FEATURE_INPUT_COLS = ["match_id", "country", "home_team", "away_team", "match_date", "info_cutoff_date",
                      "fthg", "ftag", "hs", "as_", "hst", "ast", "hc", "ac"]


def feature_frame(base: pd.DataFrame, hl: float) -> pd.DataFrame:
    """Variables EWMA (semivida hl) con caché validada: clave = hash de features.py + columnas de entrada + hl."""
    fdir = _RUN["features"]
    cache, man = fdir / f"team_ewm_hl{int(hl)}.parquet", fdir / f"team_ewm_hl{int(hl)}.json"
    key = _key(kind="features", hl=hl, features_code=sha256_file(Path(features.__file__)),
               input=frame_hash(base[FEATURE_INPUT_COLS]))
    f = None
    if cache.exists() and man.exists():
        m = json.loads(man.read_text())
        if m.get("key") == key and m.get("sha256") == sha256_file(cache):
            f = pd.read_parquet(cache)
            if len(f) != len(base) or not (f["match_id"].values == base["match_id"].values).all():
                f = None
    if f is None:
        f = features.build_features(base, hl).assign(match_id=base["match_id"].values)
        if _RUN["mode"] != "read_only":
            sha = _atomic_parquet(f, cache)
            _atomic_json({"key": key, "sha256": sha, "n_rows": int(len(f)), "hl": hl,
                          "created_utc": dt.datetime.now(dt.timezone.utc).isoformat()}, man)
    return pd.concat([base, f.drop(columns=["match_id"]).set_index(base.index)], axis=1)


# ---------------------------------------------------------------- persistencia
def _pred_path(family, cid, block):
    return OUT / "predictions" / family / f"{cid}__{block}.parquet"


def _fitlog_path(family, cid, block):
    return OUT / "fitlogs" / family / f"{cid}__{block}.parquet"


def load_preds(family) -> pd.DataFrame:
    """Predicciones completas (con manifiesto válido) de una familia. Falla si hay duplicados."""
    d = OUT / "predictions" / family
    files = sorted(d.glob("*.parquet")) if d.exists() else []
    if OUT.resolve() != PUBLISHED.resolve():  # salidas nuevas: solo las completas y verificadas
        files = [f for f in files if _manifest_ok(f)]
    if not files:
        return pd.DataFrame(columns=["match_id", "config_id", "block", "p_over"])
    P = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    dup = P.duplicated(["config_id", "block", "match_id"])
    if dup.any():
        raise val.InputValidationError(f"{family}: {int(dup.sum())} predicciones duplicadas (config, bloque, partido)")
    return P


def load_fitlogs(family) -> pd.DataFrame:
    d = OUT / "fitlogs" / family
    if d.is_dir():
        files = sorted(d.glob("*.parquet"))
        return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True) if files else pd.DataFrame()
    legacy = OUT / "fitlogs" / f"{family}.parquet"  # formato publicado de GATE 2
    return pd.read_parquet(legacy) if legacy.exists() else pd.DataFrame()


def _manifest_ok(pred_file: Path, key: str | None = None) -> bool:
    man = pred_file.with_suffix(".json")
    if not (pred_file.exists() and man.exists()):
        return False
    m = json.loads(man.read_text())
    if key is not None and m.get("key") != key:
        return False
    if m.get("sha256") != sha256_file(pred_file):
        return False
    fl = OUT / m["fitlog"] if m.get("fitlog") else None
    return fl is None or (fl.exists() and m.get("fitlog_sha256") == sha256_file(fl))


def _store(family, cid, block, preds, logs, key, params, runrec):
    _writable()
    val.unique_ids(preds, "match_id", f"{family}:{cid}:{block}")
    preds = preds.copy()
    for c in ("lam_h", "lam_a"):
        if c in preds.columns:
            preds[c] = preds[c].astype("float32")
    preds = preds.drop(columns=[c for c in ("train_max_date", "n_train") if c in preds.columns])  # están en fitlogs
    preds["config_id"], preds["block"] = cid, block
    logs = logs.copy()
    logs["config_id"], logs["block"] = cid, block
    pf, lf = _pred_path(family, cid, block), _fitlog_path(family, cid, block)
    lsha = _atomic_parquet(logs, lf)
    psha = _atomic_parquet(preds, pf)
    _atomic_json({"key": key, "family": family, "config_id": cid, "block": block, "params": params,
                  "sha256": psha, "fitlog": str(lf.relative_to(OUT)), "fitlog_sha256": lsha,
                  "n_rows": int(len(preds)), "n_unique_match_id": int(preds["match_id"].nunique()),
                  "n_nan_p_over": int(preds["p_over"].isna().sum()), "n_fits": int(len(logs)),
                  "completed_utc": dt.datetime.now(dt.timezone.utc).isoformat()}, pf.with_suffix(".json"))
    reg = _registry()
    reg.setdefault(cid, {"family": family, "params": params, "blocks": []})
    reg[cid]["blocks"] = sorted(set(reg[cid]["blocks"]) | {block})
    _atomic_json(reg, OUT / "configs.json")
    rl = json.loads((OUT / "runlog.json").read_text()) if (OUT / "runlog.json").exists() else {}
    recs = [r for r in rl.get(family, []) if not (r["config_id"] == cid and r["block"] == block)]
    rl[family] = recs + [runrec]
    _atomic_json(rl, OUT / "runlog.json")
    return preds


def _registry() -> dict:
    p = OUT / "configs.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _config_key(family, cid, params, frame, seasons, block, scope, every, columns):
    base_cols = ["match_id", "div", "season_code", "match_date", "pre_odds_capture_date_est"]
    cols = list(dict.fromkeys(base_cols + list(columns))) if columns is not None else list(frame.columns)
    return _key(kind="predictions", code=code_hash(), family=family, config_id=cid, params=params,
                seasons=list(seasons), block=block, scope=scope, every=every, columns=cols,
                input=frame_hash(frame[cols]))


def _runrec(cid, block, wall, cpu, logs, preds, parallel=False):
    return {"config_id": cid, "block": block, "wall_s": round(wall, 2), "cpu_main_s": cpu,
            "sum_fit_s": round(float(logs["wall_ms"].sum()) / 1000, 2) if len(logs) else 0.0,
            "max_rss_main_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
            "n_fits": int(len(logs)), "n_nonconverged": int((~logs["converged"]).sum()) if len(logs) else 0,
            "n_preds": int(len(preds)), "n_nan_preds": int(preds["p_over"].isna().sum()),
            **({"parallel_config_level": True} if parallel else {})}


def run_config(family, config_id, params, factory, frame, seasons, block, scope, every, columns=None):
    """Ejecuta una configuración, o la reutiliza SOLO si su manifiesto de completitud es válido."""
    _writable()
    key = _config_key(family, config_id, params, frame, seasons, block, scope, every, columns)
    pf = _pred_path(family, config_id, block)
    if _reusable() and _manifest_ok(pf, key):
        return pd.read_parquet(pf)
    t0, c0 = time.perf_counter(), resource.getrusage(resource.RUSAGE_SELF)
    preds, logs = wf.run(frame, factory, seasons, scope=scope, refit_every=every, label=config_id,
                         n_jobs=N_JOBS if scope == "division" else 1, columns=columns)
    c1 = resource.getrusage(resource.RUSAGE_SELF)
    cpu = round((c1.ru_utime + c1.ru_stime) - (c0.ru_utime + c0.ru_stime), 2)
    return _store(family, config_id, block, preds, logs, key, params,
                  _runrec(config_id, block, time.perf_counter() - t0, cpu, logs, preds))


# ---------------------------------------------------------------- universos y selección (solo bloque de ajuste)
def universe(frame: pd.DataFrame, seasons, mask_col: str | None = None) -> pd.DataFrame:
    """Universo explícito de una evaluación: partidos de `seasons` con resultado conocido y fecha de captura
    estimable (requisito point-in-time), y opcionalmente con `mask_col` verdadero.
    Toda evaluación pasa por aquí: la valla de GATE 3 se comprueba también en este punto (y registra el intento)."""
    wf.check_fence(list(seasons), "gate2.universe")
    u = frame[frame["season_code"].isin(list(seasons)) & frame["over25"].notna()
              & frame["pre_odds_capture_date_est"].notna()]
    if mask_col:
        u = u[u[mask_col].astype(bool)]
    val.unique_ids(u, "match_id", "universo")
    return u


def assert_block(pred: pd.DataFrame, frame: pd.DataFrame, allowed) -> None:
    val.unique_ids(frame, "match_id", "marco")
    seasons = pred["match_id"].map(frame.set_index("match_id")["season_code"])
    bad = sorted(set(seasons.dropna()) - set(allowed))
    if bad or seasons.isna().any():
        raise SelectionLeakError(f"La selección recibió temporadas fuera del bloque de ajuste: {bad}")


def select_best(pred: pd.DataFrame, frame: pd.DataFrame, allowed, mask_col: str | None = None,
                order: list[str] | None = None) -> tuple[str, pd.DataFrame]:
    """Mejor configuración por log loss medio en el bloque de ajuste, sobre la muestra común (preregistro §A4):
    filas del universo con predicción finita de TODAS las configuraciones comparadas. Las filas excluidas se
    cuentan (n_universe, n_excluded). Empate -> primera en `order`."""
    assert_block(pred, frame, allowed)
    dup = pred.duplicated(["config_id", "match_id"])
    if dup.any():
        raise val.InputValidationError(f"selección: {int(dup.sum())} predicciones duplicadas (config, partido)")
    wide = pred.pivot(index="match_id", columns="config_id", values="p_over")  # pivot falla ante duplicados
    U = universe(frame, allowed, mask_col)
    wide = wide.reindex(U["match_id"].values)
    ok = wide.notna().all(axis=1).to_numpy()
    yy = U["over25"].to_numpy()[ok]
    wide = wide[ok]
    tab = pd.DataFrame({"config_id": wide.columns,
                        "logloss": [ev.log_loss(yy, wide[c].to_numpy()).mean() for c in wide.columns],
                        "n": int(len(wide)), "n_universe": int(len(U)), "n_excluded": int((~ok).sum())}
                       ).sort_values("logloss", kind="mergesort")
    best = tab["logloss"].min()
    cands = tab[tab["logloss"] == best]["config_id"].tolist()
    if order:
        cands.sort(key=lambda c: order.index(c) if c in order else 10 ** 6)
    return cands[0], tab.reset_index(drop=True)


def paired(frame, pa: pd.DataFrame, pb: pd.DataFrame, seasons, mask_col=None, n_boot=2000, delta=None,
           missing: str = "error", block: int | None = None) -> dict:
    """Comparación pareada (a − b) sobre el universo explícito de `seasons` (y `mask_col`).
    missing='error': toda fila del universo debe tener predicción finita de a y de b.
    missing='common_sample': se usan las filas con ambas predicciones y se informan las excluidas
    (política preregistrada de muestra común del bloque de ajuste).
    Método principal: semanas calendario; se añade el método de GATE 2 (semanas activas) para trazabilidad."""
    c = cfg()
    U = universe(frame, seasons, mask_col)[["match_id", "match_date", "over25"]]
    a = pa[["match_id", "p_over"]].rename(columns={"p_over": "a"})
    b = pb[["match_id", "p_over"]].rename(columns={"p_over": "b"})
    m = val.merge_one_to_one(val.merge_one_to_one(U, a, context="paired:a"), b, context="paired:b")
    miss_a, miss_b = int(m["a"].isna().sum()), int(m["b"].isna().sum())
    if missing == "error" and (miss_a or miss_b):
        raise val.InputValidationError(f"paired: faltan predicciones en el universo (a: {miss_a}, b: {miss_b})")
    if missing not in ("error", "common_sample"):
        raise ValueError(missing)
    keep = m["a"].notna() & m["b"].notna()
    m = m[keep]
    bs = c["selection"]["bootstrap"]
    L = block or bs["block_weeks"]
    kw = dict(delta=delta or c["sesoi_nats"], n_boot=n_boot, seed=bs["seed"], block=L)
    res = ev.compare(m["over25"], m["a"], m["b"], m["match_date"], week_mode=bs["week_mode"], **kw)
    leg = ev.compare(m["over25"], m["a"], m["b"], m["match_date"], week_mode="active", **kw)
    res["legacy_active_weeks"] = {"delta_logloss": leg["delta_logloss"], "category": leg["category"]}
    res["sample"] = {"n_universe": int(len(U)), "n_used": int(len(m)), "n_excluded": int((~keep).sum()),
                     "missing_a": miss_a, "missing_b": miss_b, "policy": missing}
    return res


# ---------------------------------------------------------------- utilidades
def lambda_from_p(p):
    """Inversa numérica de P(Over 2,5 | λ) (monótona) — para diagnósticos cuando falta λ."""
    lo, hi = np.full_like(p, 1e-6), np.full_like(p, 15.0)
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        f = p_over25_poisson(mid)
        lo, hi = np.where(f < p, mid, lo), np.where(f < p, hi, mid)
    return 0.5 * (lo + hi)


def save_result(stage: str, res: dict) -> None:
    _writable()
    p = OUT / "results.json"
    r = json.loads(p.read_text()) if p.exists() else {}
    r[stage] = res
    _atomic_json(json.loads(json.dumps(r, default=float)), p)


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
    """specs: lista de (config_id, params, factory, columns). Calcula en paralelo y escribe en serie.
    Reutiliza una configuración SOLO si su manifiesto de completitud es válido para la misma clave."""
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor
    _writable()
    keys = {s[0]: _config_key(family, s[0], s[1], frame, seasons, block, scope, every, s[3]) for s in specs}
    todo = [s for s in specs if not (_reusable() and _manifest_ok(_pred_path(family, s[0], block),
                                                                               keys[s[0]]))]
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
            _store(family, cid, block, preds, logs, keys[cid], params[cid],
                   _runrec(cid, block, wall, None, logs, preds, parallel=True))


def benchmark_preds(frame, col, family, cid, seasons, block):
    """Guarda un benchmark (A o C) como 'predicciones' de su familia para la auditoría."""
    _writable()
    r = frame[frame["season_code"].isin(seasons)]  # igual que GATE 2 (el universo filtra al evaluar)
    key = _key(kind="benchmark", code=code_hash(), col=col, seasons=list(seasons),
               input=frame_hash(r[["match_id", col, "pre_odds_capture_date_est"]]))
    if _reusable() and _manifest_ok(_pred_path(family, cid, block), key):
        return
    p = pd.DataFrame({"match_id": r["match_id"].values, "p_over": r[col].values,
                      "fit_tau": r["pre_odds_capture_date_est"].values})
    logs = pd.DataFrame({"label": [cid], "converged": [True], "wall_ms": [0.0]})
    _store(family, cid, block, p, logs, key, {"source": col}, _runrec(cid, block, 0.0, None, logs, p))

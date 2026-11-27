"""Motor walk-forward point-in-time (GATE 2).

Garantías (probadas en tests/test_walkforward.py):
1. En cada fecha de ajuste τ, el modelo recibe SOLO filas con match_date < τ (aserción +
   `train_max_date` registrado por predicción).
2. Al predecir, el modelo recibe SOLO columnas pre-partido (lista blanca): nunca resultados,
   estadísticas del partido ni cuotas de cierre de las filas que predice.
3. Una predicción para un partido con captura estimada c usa un ajuste con τ ≤ c.
4. Valla GATE 3: se niega a evaluar temporadas posteriores a `fence_max_eval_season`
   (configs/gate2.json) salvo `allow_beyond_fence=True`, reservado a GATE 3 autorizado.
5. Rechaza datos reservados (holdout.assert_no_reserved).
"""
from __future__ import annotations

import json
import multiprocessing as mp
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

from . import holdout, paths

PREMATCH_EXACT = {"match_id", "div", "country", "competition", "season_code", "season", "match_date",
                  "kickoff_time_uk", "home_team", "away_team", "weekday", "pre_odds_capture_date_est",
                  "info_cutoff_date", "capture_rule_ambiguous", "ou_pre_avg_source"}
PREMATCH_PREFIXES = ("ou_pre_", "x12_pre_", "feat_", "inp_", "p_A", "p_C", "A_", "Astar_")


class FenceError(RuntimeError):
    """Intento de evaluar el bloque de validación (GATE 3) sin autorización."""


def gate2_config() -> dict:
    return json.loads((paths.CONFIGS / "gate2.json").read_text())


def prematch_view(rows: pd.DataFrame) -> pd.DataFrame:
    keep = [c for c in rows.columns if c in PREMATCH_EXACT or c.startswith(PREMATCH_PREFIXES)]
    return rows[keep]


def check_fence(eval_seasons, allow_beyond_fence: bool = False) -> None:
    fence = gate2_config()["blocks"]["fence_max_eval_season"]
    bad = sorted(s for s in eval_seasons if s > fence)
    if bad and not allow_beyond_fence:
        raise FenceError(f"Temporadas {bad} > valla {fence}: el bloque de validación pertenece a GATE 3 "
                         f"(requiere autorización expresa del usuario).")


@dataclass
class FitLog:
    label: str
    scope: str
    fit_tau: str
    n_train: int
    train_max_date: str
    wall_ms: float
    converged: bool
    iterations: int
    message: str
    extra: str = ""


def _schedule(taus: np.ndarray, every: int) -> list[tuple[pd.Timestamp, pd.Timestamp | None]]:
    """Fechas de ajuste (cada `every` capturas) y su intervalo de validez [τ_k, τ_{k+1})."""
    taus = np.sort(np.unique(taus))
    fits = taus[::every]
    return [(pd.Timestamp(fits[i]), pd.Timestamp(fits[i + 1]) if i + 1 < len(fits) else None) for i in range(len(fits))]


def _run_scope(df: pd.DataFrame, targets: pd.DataFrame, factory, every: int, label: str, scope: str):
    preds, logs = [], []
    model = factory()
    for tau, nxt in _schedule(targets["pre_odds_capture_date_est"].values, every):
        cap = targets["pre_odds_capture_date_est"]
        grp = targets[(cap >= tau) & ((cap < nxt) if nxt is not None else True)]
        if grp.empty:
            continue
        train = df[df["match_date"] < tau]
        tmax = train["match_date"].max() if len(train) else pd.NaT
        if len(train) and not (tmax < tau):
            raise AssertionError("Fuga temporal: entrenamiento con fecha >= τ")
        t0 = time.perf_counter()
        info = model.fit(train, tau) or {}
        wall = (time.perf_counter() - t0) * 1000
        view = prematch_view(grp)
        p = np.asarray(model.predict(view), dtype=float)
        out = pd.DataFrame({"match_id": grp["match_id"].values, "p_over": p, "fit_tau": tau,
                            "train_max_date": tmax, "n_train": len(train)})
        if hasattr(model, "predict_extra"):  # salidas auxiliares (p. ej. λ) para diagnósticos/auditoría
            for k, v in model.predict_extra(view).items():
                out[k] = np.asarray(v, dtype=float)
        preds.append(out)
        logs.append(FitLog(label, scope, str(tau.date()), int(len(train)), str(tmax.date()) if pd.notna(tmax) else "",
                           round(wall, 2), bool(info.get("converged", True)), int(info.get("iterations", 0)),
                           str(info.get("message", ""))[:80], json.dumps(info.get("extra", {}), default=float)))
    return preds, logs


_G: dict = {}


def _init(df, targets, factory, every, label):
    _G.update(df=df, targets=targets, factory=factory, every=every, label=label)


def _div_job(div):
    df, t = _G["df"], _G["targets"]
    return _run_scope(df[df["div"] == div], t[t["div"] == div], _G["factory"], _G["every"], _G["label"], div)


def run(df: pd.DataFrame, factory, eval_seasons, scope: str = "division", refit_every: int = 1,
        label: str = "", n_jobs: int = 1, allow_beyond_fence: bool = False,
        columns: list[str] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Ejecuta un walk-forward. `factory()` devuelve un modelo con fit(train, tau)->dict y predict(rows)->array.
    `columns`: subconjunto de columnas que necesita el modelo (reduce el coste de enviar datos a procesos)."""
    holdout.assert_no_reserved(df, f"walkforward:{label}")
    if columns is not None:
        base = ["match_id", "div", "season_code", "match_date", "pre_odds_capture_date_est"]
        df = df[list(dict.fromkeys(base + list(columns)))]
    eval_seasons = list(eval_seasons)
    check_fence(eval_seasons, allow_beyond_fence)
    targets = df[df["season_code"].isin(eval_seasons) & df["pre_odds_capture_date_est"].notna()]
    if scope == "division":
        divs = sorted(targets["div"].unique())
        if n_jobs > 1:
            ctx = mp.get_context("forkserver")  # evita fork() con hilos activos (riesgo de bloqueo)
            with ProcessPoolExecutor(n_jobs, mp_context=ctx, initializer=_init,
                                     initargs=(df, targets, factory, refit_every, label)) as ex:
                results = list(ex.map(_div_job, divs))
        else:
            _init(df, targets, factory, refit_every, label)
            results = [_div_job(d) for d in divs]
    elif scope == "pooled":
        results = [_run_scope(df, targets, factory, refit_every, label, "pooled")]
    else:
        raise ValueError(scope)
    preds = pd.concat([p for r in results for p in r[0]], ignore_index=True) if results else pd.DataFrame()
    logs = pd.DataFrame([asdict(l) for r in results for l in r[1]])
    # garantía 3: el ajuste usado nunca es posterior a la captura del partido
    chk = preds.merge(df[["match_id", "pre_odds_capture_date_est"]], on="match_id")
    if not (chk["fit_tau"] <= chk["pre_odds_capture_date_est"]).all():
        raise AssertionError("Ajuste posterior a la captura")
    return preds, logs

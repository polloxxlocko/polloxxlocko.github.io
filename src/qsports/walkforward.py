"""Motor walk-forward point-in-time (GATE 2).

Garantías (probadas en tests/test_walkforward.py):
1. En cada fecha de ajuste τ, el modelo recibe SOLO filas con match_date < τ (aserción +
   `train_max_date` y `n_train` registrados POR AJUSTE en el FitLog). `run` también los devuelve por
   predicción, pero las predicciones persistidas (gate2._store) los omiten: se enlazan con su ajuste
   por (config_id, block, scope, fit_tau), donde scope = división del partido o 'pooled'.
2. Al predecir, el modelo recibe SOLO columnas pre-partido (lista blanca): nunca resultados,
   estadísticas del partido ni cuotas de cierre de las filas que predice.
3. Una predicción para un partido con captura estimada c usa un ajuste con τ ≤ c.
4. Valla GATE 3: se niega a evaluar temporadas posteriores a `fence_max_eval_season`
   (configs/gate2.json) salvo con un archivo de autorización válido (creado SOLO por instrucción
   expresa del usuario) ligado al hash de los candidatos congelados. Todo intento de cruzar la
   valla, permitido o rechazado, se anota en logs/GATE3_FENCE_LOG.jsonl (append-only).
5. Rechaza datos reservados (holdout.assert_no_reserved).
"""
from __future__ import annotations

import datetime as dt
import hashlib
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


def _sha256(p) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _fence_log(event: dict) -> None:
    paths.FENCE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with paths.FENCE_LOG.open("a") as f:
        f.write(json.dumps({"at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), **event},
                           ensure_ascii=False, default=str) + "\n")


def gate3_authorization() -> dict:
    """Valida la autorización de GATE 3. Lanza FenceError si falta o no es válida."""
    fc = gate2_config()["gate3_fence"]
    p = paths.ROOT / fc["authorization_file"]
    if not p.exists():
        raise FenceError(f"No existe {fc['authorization_file']}: GATE 3 no está autorizado.")
    auth = json.loads(p.read_text())
    missing = [k for k in fc["required_fields"] if not auth.get(k)]
    if missing:
        raise FenceError(f"Autorización de GATE 3 incompleta: faltan {missing}.")
    cand = paths.ROOT / fc["frozen_candidates_file"]
    if not cand.exists():
        raise FenceError(f"No existe {fc['frozen_candidates_file']}: los candidatos no están congelados.")
    if auth["frozen_candidates_sha256"] != _sha256(cand):
        raise FenceError("Los candidatos congelados cambiaron después de la autorización (hash distinto).")
    return auth


def check_fence(eval_seasons, label: str = "", holdout_authorization: dict | None = None) -> None:
    """Valla. Sin temporadas posteriores a la valla no hace nada. Con ellas registra el intento (permitido o
    rechazado) y exige: para temporadas de desarrollo (2022/23-2023/24) la autorización de GATE 3; para el holdout
    la autorización del holdout (recibida y verificada de nuevo aquí); la reserva no se admite nunca."""
    fence = gate2_config()["blocks"]["fence_max_eval_season"]
    bad = sorted(s for s in eval_seasons if s > fence)
    if not bad:
        return
    res = [s for s in bad if paths.partition_of(s) == "reserve"]
    hold = [s for s in bad if paths.partition_of(s) == "holdout"]
    if res:
        _fence_log({"outcome": "refused", "label": label, "seasons": bad, "fence": fence,
                    "reason": "reserva sellada: nunca evaluable en este protocolo"})
        raise FenceError(f"Temporadas {res} de la reserva sellada: no evaluables.")
    if hold:
        try:
            if holdout_authorization is None:
                raise holdout.ReservedDataError("no se recibió autorización del holdout")
            holdout.verify_holdout_authorization(holdout_authorization)
        except holdout.ReservedDataError as e:
            _fence_log({"outcome": "refused", "label": label, "seasons": bad, "fence": fence, "reason": str(e)})
            raise FenceError(f"Temporadas {hold} del holdout sellado: requiere autorización expresa. {e}") from e
        _fence_log({"outcome": "allowed-holdout", "label": label, "seasons": hold, "fence": fence,
                    "authorized_by": holdout_authorization["authorized_by"],
                    "protocol_freeze_sha256": holdout_authorization["protocol_freeze_sha256"]})
        bad = [s for s in bad if s not in hold]
        if not bad:
            return
    try:
        auth = gate3_authorization()
    except FenceError as e:
        _fence_log({"outcome": "refused", "label": label, "seasons": bad, "fence": fence, "reason": str(e)})
        raise FenceError(f"Temporadas {bad} > valla {fence}: el bloque de validación pertenece a GATE 3 "
                         f"(requiere autorización expresa del usuario). {e}") from e
    _fence_log({"outcome": "allowed", "label": label, "seasons": bad, "fence": fence,
                "authorized_by": auth["authorized_by"], "frozen_candidates_sha256": auth["frozen_candidates_sha256"]})


def fence_log_summary() -> dict:
    """Resumen del registro de la valla para `verify`: un cruce 'allowed' sin autorización válida es un fallo."""
    if not paths.FENCE_LOG.exists():
        return {"present": False, "allowed": 0, "refused": 0, "ok": True,
                "note": "sin registro: ningún intento de cruzar la valla"}
    ev = [json.loads(x) for x in paths.FENCE_LOG.read_text().splitlines() if x.strip()]
    allowed = [e for e in ev if e.get("outcome") == "allowed"]
    allowed_h = [e for e in ev if e.get("outcome") == "allowed-holdout"]
    refused = [e for e in ev if e.get("outcome") == "refused"]
    ok = True
    if allowed:
        try:
            auth = gate3_authorization()
            ok = all(e.get("frozen_candidates_sha256") == auth["frozen_candidates_sha256"] for e in allowed)
        except FenceError:
            ok = False
    if allowed_h:
        try:
            ha = holdout.holdout_authorization()
            ok = ok and all(e.get("protocol_freeze_sha256") == ha["protocol_freeze_sha256"] for e in allowed_h)
        except holdout.ReservedDataError:
            ok = False
    return {"present": True, "allowed": len(allowed), "allowed_holdout": len(allowed_h), "refused": len(refused),
            "ok": ok}


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
        label: str = "", n_jobs: int = 1, columns: list[str] | None = None,
        holdout_authorization: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Ejecuta un walk-forward. `factory()` devuelve un modelo con fit(train, tau)->dict y predict(rows)->array.
    `columns`: subconjunto de columnas que necesita el modelo (reduce el coste de enviar datos a procesos).
    `holdout_authorization`: solo para la prueba final autorizada (se verifica de nuevo; la reserva sigue prohibida)."""
    holdout.assert_no_reserved(df, f"walkforward:{label}", allow_holdout=holdout_authorization)
    if columns is not None:
        base = ["match_id", "div", "season_code", "match_date", "pre_odds_capture_date_est"]
        df = df[list(dict.fromkeys(base + list(columns)))]
    eval_seasons = list(eval_seasons)
    check_fence(eval_seasons, label, holdout_authorization)
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

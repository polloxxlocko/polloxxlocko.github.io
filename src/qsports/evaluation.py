"""Evaluador estadístico (GATE 2). Funciones puras y probadas con datos sintéticos.

Convenciones:
- Pérdidas por observación (menor = mejor). Diferencias pareadas d = pérdida_modelo − pérdida_ref
  (d < 0: el modelo es mejor).
- Incertidumbre: bootstrap por bloques móviles de SEMANAS (todas las ligas de una semana
  juntas: capta shocks comunes; bloques consecutivos: capta dependencia serial).
- Diebold-Mariano con varianza HAC (Bartlett) sobre totales semanales, coherente con el
  estimador de razón usado por el bootstrap.
- `decision_category` implementa la partición mutuamente excluyente de
  EXPERIMENTAL_PROTOCOL.md §6.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import optimize, stats

EPS = 1e-12


# ---------------------------------------------------------------- pérdidas
def log_loss(y, p):
    y = np.asarray(y, dtype=float)
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def brier(y, p):
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    return (p - y) ** 2


# ---------------------------------------------------------------- calibración
def _logit(p):
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


def calibration(y, p) -> dict:
    """Pendiente (de logit y ~ a + b·logit p) e intercepto 'en grande' (logit y ~ a + offset(logit p)).
    Ajuste por máxima verosimilitud (L-BFGS). Calibración perfecta: pendiente 1, intercepto 0."""
    y = np.asarray(y, dtype=float)
    z = _logit(p)

    def nll(theta, offset_only=False):
        a, b = (theta[0], 1.0) if offset_only else theta
        eta = a + b * z
        mu = 1 / (1 + np.exp(-eta))
        ll = np.sum(np.logaddexp(0, eta) - y * eta)
        g_a = np.sum(mu - y)
        if offset_only:
            return ll, np.array([g_a])
        return ll, np.array([g_a, np.sum((mu - y) * z)])

    r2 = optimize.minimize(nll, x0=np.array([0.0, 1.0]), jac=True, method="L-BFGS-B")
    r1 = optimize.minimize(lambda t: nll(t, True), x0=np.array([0.0]), jac=True, method="L-BFGS-B")
    return {"slope": float(r2.x[1]), "slope_model_intercept": float(r2.x[0]),
            "intercept_in_the_large": float(r1.x[0]), "converged": bool(r2.success and r1.success)}


def reliability_table(y, p, n_bins: int = 10) -> pd.DataFrame:
    """Bins de igual frecuencia: p medio, frecuencia observada, n."""
    d = pd.DataFrame({"y": np.asarray(y, float), "p": np.asarray(p, float)})
    d["bin"] = pd.qcut(d["p"].rank(method="first"), n_bins, labels=False)
    t = d.groupby("bin").agg(p_mean=("p", "mean"), y_rate=("y", "mean"), n=("y", "size")).reset_index()
    return t


def ece(y, p, n_bins: int = 10) -> float:
    t = reliability_table(y, p, n_bins)
    return float(np.sum(t["n"] * (t["p_mean"] - t["y_rate"]).abs()) / t["n"].sum())


def murphy_decomposition(y, p_binned) -> dict:
    """Brier = fiabilidad − resolución + incertidumbre, exacta si p es constante dentro de cada bin
    (p_binned: pronósticos discretos)."""
    y = np.asarray(y, float)
    p = np.asarray(p_binned, float)
    ybar = y.mean()
    rel = res = 0.0
    for v in np.unique(p):
        m = p == v
        nk, ok = m.sum(), y[m].mean()
        rel += nk * (v - ok) ** 2
        res += nk * (ok - ybar) ** 2
    n = len(y)
    return {"reliability": rel / n, "resolution": res / n, "uncertainty": ybar * (1 - ybar),
            "brier": float(np.mean((p - y) ** 2))}


def sharpness(p) -> dict:
    p = np.asarray(p, float)
    return {"sd": float(p.std(ddof=1)), "mean_abs_from_half": float(np.mean(np.abs(p - 0.5)))}


def auc(y, p) -> float:
    """AUC por rangos (Mann-Whitney), con empates promediados."""
    y = np.asarray(y, float)
    r = stats.rankdata(np.asarray(p, float))
    n1 = y.sum()
    n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


# ---------------------------------------------------------------- incertidumbre
def week_ids(dates) -> np.ndarray:
    """Semana calendario lunes-domingo como entero ordenable."""
    d = pd.to_datetime(pd.Series(dates))
    return (d - pd.to_timedelta(d.dt.weekday, unit="D")).dt.normalize().values.astype("datetime64[D]").astype(np.int64)


def _weekly_totals(d, weeks):
    df = pd.DataFrame({"d": np.asarray(d, float), "w": np.asarray(weeks)})
    g = df.groupby("w")["d"].agg(["sum", "count"]).sort_index()
    return g["sum"].to_numpy(), g["count"].to_numpy().astype(float)


def block_bootstrap_mean(d, weeks, block: int = 4, n_boot: int = 10_000, seed: int = 20261127,
                         alpha: float = 0.05, return_reps: bool = False) -> dict:
    """Bootstrap por bloques móviles de semanas del estimador de razón Σd/Σn."""
    S, N = _weekly_totals(d, weeks)
    W = len(S)
    est = S.sum() / N.sum()
    L = max(1, min(block, W))
    k = int(math.ceil(W / L))
    cS = np.concatenate([[0.0], np.cumsum(S)])
    cN = np.concatenate([[0.0], np.cumsum(N)])
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, W - L + 1, size=(n_boot, k))
    bs = (cS[starts + L] - cS[starts]).sum(axis=1)
    bn = (cN[starts + L] - cN[starts]).sum(axis=1)
    reps = bs / bn
    lo, hi = np.quantile(reps, [alpha / 2, 1 - alpha / 2])
    out = {"mean": float(est), "lo": float(lo), "hi": float(hi), "n": int(N.sum()), "weeks": int(W),
           "block_weeks": L, "n_boot": n_boot, "seed": seed}
    if return_reps:
        out["reps"] = reps
    return out


def diebold_mariano(d, weeks, lag: int | None = None) -> dict:
    """Prueba de igualdad de pérdida esperada (H0: E[d] = 0) con varianza HAC (Bartlett) sobre
    totales semanales centrados z_w = S_w − N_w·d̄."""
    S, N = _weekly_totals(d, weeks)
    W = len(S)
    dbar = S.sum() / N.sum()
    z = S - N * dbar
    q = lag if lag is not None else int(math.floor(4 * (W / 100) ** (2 / 9)))
    lrv = float(np.dot(z, z))
    for j in range(1, q + 1):
        lrv += 2 * (1 - j / (q + 1)) * float(np.dot(z[j:], z[:-j]))
    var = lrv / N.sum() ** 2
    if var <= 0:
        return {"stat": float("nan"), "p_value": 1.0, "mean": float(dbar), "lag": q}
    t = dbar / math.sqrt(var)
    return {"stat": float(t), "p_value": float(2 * stats.norm.sf(abs(t))), "mean": float(dbar), "lag": q,
            "se": math.sqrt(var)}


def design_effect(d, clusters) -> float:
    """Efecto de diseño de la media por agrupamiento en clusters (varianza cluster / varianza iid)."""
    S, N = _weekly_totals(d, clusters)
    n = N.sum()
    m = S.sum() / n
    v_cluster = np.sum((S - N * m) ** 2) / n ** 2
    v_iid = np.var(np.asarray(d, float), ddof=1) / n
    return float(v_cluster / v_iid) if v_iid > 0 else float("nan")


def mde(sigma: float, n: float, deff: float = 1.0, alpha: float = 0.05, power: float = 0.80) -> float:
    """Mínimo efecto detectable (bilateral)."""
    return float((stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)) * sigma * math.sqrt(deff) / math.sqrt(n))


# ---------------------------------------------------------------- decisión
CATEGORIES = ("S-R", "S-NR", "EQ", "INC", "I-NR", "I-R")


def decision_category(lo: float, hi: float, delta: float) -> str:
    """Partición mutuamente excluyente del protocolo §6 (diferencias: modelo − referencia; <0 mejor)."""
    if not (lo <= hi):
        raise ValueError("Se requiere lo <= hi")
    if delta <= 0:
        raise ValueError("delta debe ser > 0")
    if hi < -delta:
        return "S-R"
    if hi < 0:
        return "S-NR"
    if lo > delta:
        return "I-R"
    if lo > 0:
        return "I-NR"
    if lo > -delta and hi < delta:
        return "EQ"
    return "INC"


def compare(y, p_model, p_ref, dates, delta: float, n_boot: int = 10_000, seed: int = 20261127,
            block: int = 4) -> dict:
    """Comparación pareada completa de dos pronósticos sobre la misma muestra."""
    y = np.asarray(y, float)
    d = log_loss(y, p_model) - log_loss(y, p_ref)
    w = week_ids(dates)
    bb = block_bootstrap_mean(d, w, block=block, n_boot=n_boot, seed=seed)
    dm = diebold_mariano(d, w)
    db = brier(y, p_model) - brier(y, p_ref)
    return {"n": int(len(y)), "delta_logloss": bb, "category": decision_category(bb["lo"], bb["hi"], delta),
            "dm": dm, "delta_brier": float(db.mean()), "sd_delta": float(d.std(ddof=1)),
            "deff_week": design_effect(d, w),
            "logloss_model": float(log_loss(y, p_model).mean()), "logloss_ref": float(log_loss(y, p_ref).mean())}


def describe_forecast(y, p) -> dict:
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    return {"n": int(len(y)), "logloss": float(log_loss(y, p).mean()), "brier": float(brier(y, p).mean()),
            **{f"cal_{k}": v for k, v in calibration(y, p).items()}, "ece": ece(y, p),
            **{f"sharp_{k}": v for k, v in sharpness(p).items()}, "auc": auc(y, p),
            "mean_p": float(p.mean()), "base_rate": float(y.mean())}

"""Evaluador estadístico (GATE 2). Funciones puras y probadas con datos sintéticos.

Convenciones:
- Pérdidas por observación (menor = mejor). Diferencias pareadas d = pérdida_modelo − pérdida_ref
  (d < 0: el modelo es mejor).
- Entradas validadas (qsports.validation): probabilidades finitas en [0, 1], resultados 0/1,
  mismas dimensiones, sin faltantes. Nada se recorta ni se descarta en silencio.
- Incertidumbre: bootstrap por bloques móviles de SEMANAS CALENDARIO (GATE 2.1). La serie
  semanal cubre todas las semanas lunes-domingo entre la primera y la última observación,
  incluidas las semanas sin partidos (S = 0, N = 0): un bloque de L semanas son L semanas
  de calendario consecutivas, también a través de pausas. Todas las ligas de una semana van
  juntas (shocks comunes). Alternativa documentada: `week_mode="active"` (bloques de L
  semanas CON partidos, el método efectivamente usado en GATE 2; se conserva solo para
  comparar con lo publicado y como análisis de sensibilidad).
- Diebold-Mariano con varianza HAC (Bartlett) sobre totales semanales de la misma serie,
  coherente con el estimador de razón usado por el bootstrap.
- `decision_category` implementa la partición mutuamente excluyente de
  EXPERIMENTAL_PROTOCOL.md §6.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import optimize, stats

from . import validation as val
from .validation import InputValidationError

WEEK_MODES = ("calendar", "active")


def _yp(y, p, ny="y", np_="p"):
    y, p = val.outcomes(y, ny), val.probabilities(p, np_)
    val.same_length(**{ny: y, np_: p})
    return y, p


# ---------------------------------------------------------------- pérdidas
def log_loss(y, p):
    """−[y·log p + (1−y)·log(1−p)], exacta (sin recorte). Una probabilidad 0 o 1 que contradice el
    resultado produce pérdida infinita y se rechaza explícitamente."""
    y, p = _yp(y, p)
    with np.errstate(divide="ignore"):
        out = np.where(y == 1, -np.log(p), -np.log1p(-p))
    if not np.isfinite(out).all():
        raise InputValidationError(f"log loss infinita en {int((~np.isfinite(out)).sum())} filas "
                                   f"(probabilidad 0 o 1 contradicha por el resultado)")
    return out


def brier(y, p):
    y, p = _yp(y, p)
    return (p - y) ** 2


# ---------------------------------------------------------------- calibración
def _logit(p):
    p = np.asarray(p, dtype=float)
    if ((p <= 0) | (p >= 1)).any():
        raise InputValidationError("calibración: logit indefinido para probabilidades 0 o 1")
    return np.log(p / (1 - p))


def calibration(y, p) -> dict:
    """Pendiente (de logit y ~ a + b·logit p) e intercepto 'en grande' (logit y ~ a + offset(logit p)).
    Ajuste por máxima verosimilitud (L-BFGS). Calibración perfecta: pendiente 1, intercepto 0."""
    y, p = _yp(y, p)
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
    y, p = _yp(y, p)
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
    y, p = _yp(y, p_binned, np_="p_binned")
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
    p = val.probabilities(p)
    return {"sd": float(p.std(ddof=1)), "mean_abs_from_half": float(np.mean(np.abs(p - 0.5)))}


def auc(y, p) -> float:
    """AUC por rangos (Mann-Whitney), con empates promediados."""
    y, p = _yp(y, p)
    r = stats.rankdata(p)
    n1 = y.sum()
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        raise InputValidationError("AUC indefinida: se requieren ambos resultados")
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


# ---------------------------------------------------------------- incertidumbre
def week_ids(dates) -> np.ndarray:
    """Índice de semana calendario lunes-domingo: entero tal que semanas de calendario
    consecutivas tienen índices consecutivos (lunes en días desde 1970-01-01, dividido por 7)."""
    d = val.dates(dates)
    monday = (d - pd.to_timedelta(d.dt.weekday, unit="D")).dt.normalize()
    days = monday.values.astype("datetime64[D]").astype(np.int64)
    if not (days % 7 == 4).all():  # 1970-01-05 (día 4) fue lunes
        raise AssertionError("week_ids: cálculo de lunes inconsistente")
    return days // 7


def _weekly_totals(d, weeks, mode: str = "calendar"):
    """Totales semanales (Σd, n) ordenados. mode='calendar': TODAS las semanas entre la primera y la
    última (las semanas sin partidos con 0, 0). mode='active': solo semanas con partidos."""
    if mode not in WEEK_MODES:
        raise ValueError(f"week_mode debe ser uno de {WEEK_MODES}")
    d = np.asarray(d, float)
    w = np.asarray(weeks)
    val.same_length(d=d, weeks=w)
    if not np.isfinite(d).all():
        raise InputValidationError("diferencias no finitas")
    if not np.issubdtype(w.dtype, np.integer):
        raise InputValidationError("weeks debe ser un índice entero de semana calendario (use week_ids)")
    g = pd.DataFrame({"d": d, "w": w}).groupby("w")["d"].agg(["sum", "count"]).sort_index()
    if mode == "calendar":
        g = g.reindex(np.arange(g.index.min(), g.index.max() + 1), fill_value=0)
    return g["sum"].to_numpy(float), g["count"].to_numpy().astype(float)


def block_bootstrap_mean(d, weeks, block: int = 4, n_boot: int = 10_000, seed: int = 20261127,
                         alpha: float = 0.05, return_reps: bool = False, week_mode: str = "calendar") -> dict:
    """Bootstrap por bloques móviles de semanas del estimador de razón Σd/Σn.
    Con week_mode='calendar' un bloque son `block` semanas de calendario consecutivas (puede contener
    semanas vacías); se remuestrean ceil(W/block) bloques para cubrir W semanas de calendario."""
    S, N = _weekly_totals(d, weeks, week_mode)
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
    if (bn == 0).any():
        raise InputValidationError(f"{int((bn == 0).sum())} réplicas sin observaciones (bloques demasiado cortos "
                                   f"frente a las pausas); aumente el bloque")
    reps = bs / bn
    lo, hi = np.quantile(reps, [alpha / 2, 1 - alpha / 2])
    out = {"mean": float(est), "lo": float(lo), "hi": float(hi), "n": int(N.sum()), "weeks": int(W),
           "weeks_with_matches": int((N > 0).sum()), "block_weeks": L, "week_mode": week_mode,
           "n_boot": n_boot, "seed": seed, "se_boot": float(np.std(reps, ddof=1))}
    if return_reps:
        out["reps"] = reps
    return out


def diebold_mariano(d, weeks, lag: int | None = None, week_mode: str = "calendar") -> dict:
    """Prueba de igualdad de pérdida esperada (H0: E[d] = 0) con varianza HAC (Bartlett) sobre
    totales semanales centrados z_w = S_w − N_w·d̄ (semanas calendario: los rezagos son semanas)."""
    S, N = _weekly_totals(d, weeks, week_mode)
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
            "se": math.sqrt(var), "week_mode": week_mode}


def weekly_autocorrelation(d, weeks, max_lag: int = 8, week_mode: str = "calendar") -> list[float]:
    """Autocorrelación (rezagos 1..max_lag, en semanas) de los totales semanales centrados z_w = S_w − N_w·d̄.
    Diagnóstico de la dependencia serial que el bloque del bootstrap debe capturar."""
    S, N = _weekly_totals(d, weeks, week_mode)
    z = S - N * (S.sum() / N.sum())
    den = float(np.dot(z, z))
    return [float(np.dot(z[k:], z[:-k]) / den) if den > 0 and k < len(z) else float("nan") for k in range(1, max_lag + 1)]


def design_effect(d, clusters) -> float:
    """Efecto de diseño de la media por agrupamiento en clusters (varianza cluster / varianza iid).
    Los clusters vacíos no aportan (se usan solo semanas con partidos)."""
    S, N = _weekly_totals(d, clusters, "active")
    n = N.sum()
    m = S.sum() / n
    v_cluster = np.sum((S - N * m) ** 2) / n ** 2
    v_iid = np.var(np.asarray(d, float), ddof=1) / n
    return float(v_cluster / v_iid) if v_iid > 0 else float("nan")


def mde(sigma: float, n: float, deff: float = 1.0, alpha: float = 0.05, power: float = 0.80) -> float:
    """Mínimo efecto detectable para SUPERIORIDAD frente a 0 (bilateral): |θ| tal que P(U < 0) = potencia."""
    return float((stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)) * sigma * math.sqrt(deff) / math.sqrt(n))


# ---------------------------------------------------------------- potencia: superioridad frente a equivalencia
def prob_categories(theta: float, se: float, delta: float, alpha: float = 0.05) -> dict:
    """Probabilidades (aprox. normal: Δ̂ ~ N(θ, se²), IC = Δ̂ ± z·se) de cada resultado de la partición §6."""
    z = stats.norm.ppf(1 - alpha / 2)
    F = lambda x: float(stats.norm.cdf((x - theta) / se))  # noqa: E731

    def band(a, b):  # P(a < Δ̂ < b)
        return max(0.0, F(b) - F(a)) if b > a else 0.0
    # U = Δ̂ + z·se ; L = Δ̂ − z·se
    p = {"S-R": F(-delta - z * se), "S-NR": band(-delta - z * se, -z * se),
         "I-R": 1 - F(delta + z * se), "I-NR": band(z * se, delta + z * se)}
    lo_eq, hi_eq = max(-delta + z * se, -z * se), min(delta - z * se, z * se)
    p["EQ"] = band(lo_eq, hi_eq)
    p["INC"] = max(0.0, 1 - sum(p.values()))
    p["CI_within_margin"] = band(-delta + z * se, delta - z * se)  # |Δ| < δ demostrado (S-NR ∪ EQ ∪ I-NR)
    return p


def power_profile(se: float, delta: float, alpha: float = 0.05, power: float = 0.80) -> dict:
    """Distingue la potencia para detectar SUPERIORIDAD de la potencia para demostrar EQUIVALENCIA.

    - mde_superiority_vs_zero: mejora real |θ| necesaria para que P(U < 0) = potencia.
    - mde_superiority_relevant: mejora real necesaria para que P(U < −δ) = potencia (categoría S-R).
    - p_equivalence_at_zero: si la diferencia real es 0, probabilidad de que el IC quede dentro de
      (−δ, δ) (equivalencia práctica demostrada).
    - max_theta_equivalence: mayor |θ| real para el que esa probabilidad aún alcanza la potencia.
    - se_needed_equivalence: error estándar necesario para que p_equivalence_at_zero = potencia.
    """
    z, zb = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    p0 = prob_categories(0.0, se, delta, alpha)
    se_need = delta / (z + stats.norm.ppf((1 + power) / 2))
    if p0["CI_within_margin"] >= power:
        max_theta = optimize.brentq(lambda t: prob_categories(t, se, delta, alpha)["CI_within_margin"] - power,
                                    0.0, delta)
    else:
        max_theta = None
    return {"se": float(se), "delta": delta, "alpha": alpha, "power_target": power,
            "mde_superiority_vs_zero": float((z + zb) * se), "mde_superiority_relevant": float(delta + (z + zb) * se),
            "p_equivalence_at_zero": p0["CI_within_margin"], "p_EQ_category_at_zero": p0["EQ"],
            "max_theta_equivalence": None if max_theta is None else float(max_theta),
            "se_needed_equivalence": float(se_need), "assumption": "Δ̂ ~ Normal(θ, se²); IC percentil ≈ Δ̂ ± z·se"}


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
            block: int = 4, week_mode: str = "calendar") -> dict:
    """Comparación pareada completa de dos pronósticos sobre la misma muestra (entradas validadas)."""
    y = val.outcomes(y)
    pm, pr = val.probabilities(p_model, "p_model"), val.probabilities(p_ref, "p_ref")
    dts = val.dates(dates)
    val.same_length(y=y, p_model=pm, p_ref=pr, dates=dts)
    lm, lr = log_loss(y, pm), log_loss(y, pr)
    d = lm - lr
    w = week_ids(dts)
    bb = block_bootstrap_mean(d, w, block=block, n_boot=n_boot, seed=seed, week_mode=week_mode)
    dm = diebold_mariano(d, w, week_mode=week_mode)
    db = brier(y, pm) - brier(y, pr)
    return {"n": int(len(y)), "delta_logloss": bb, "category": decision_category(bb["lo"], bb["hi"], delta),
            "dm": dm, "delta_brier": float(db.mean()), "sd_delta": float(d.std(ddof=1)),
            "deff_week": design_effect(d, w), "week_mode": week_mode,
            "logloss_model": float(lm.mean()), "logloss_ref": float(lr.mean())}


def describe_forecast(y, p) -> dict:
    y, p = _yp(y, p)
    return {"n": int(len(y)), "logloss": float(log_loss(y, p).mean()), "brier": float(brier(y, p).mean()),
            **{f"cal_{k}": v for k, v in calibration(y, p).items()}, "ece": ece(y, p),
            **{f"sharp_{k}": v for k, v in sharpness(p).items()}, "auc": auc(y, p),
            "mean_p": float(p.mean()), "base_rate": float(y.mean())}

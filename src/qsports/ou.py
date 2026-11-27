"""Mercado Over/Under 2,5 goles: liquidación y fórmula analítica Poisson.

Liquidación (tiempo reglamentario, sin devolución): Over si FTHG + FTAG >= 3.
Football-Data registra goles a tiempo completo (90' + descuento); no incluye prórroga
en partidos de liga.
"""
from __future__ import annotations

import math

import numpy as np

LINE = 2.5


def settle_over25(fthg, ftag):
    """1.0 si Over 2,5; 0.0 si Under; NaN si falta algún marcador."""
    h = np.asarray(fthg, dtype=float)
    a = np.asarray(ftag, dtype=float)
    tot = h + a
    return np.where(np.isfinite(tot), (tot > LINE).astype(float), np.nan)


def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam**k / math.factorial(k)


def p_over25_poisson(lam_total):
    """P(Over 2,5) bajo goles totales ~ Poisson(lam_total) (independencia => suma Poisson).
    P(Over) = 1 - e^{-λ}(1 + λ + λ²/2). Exacto: no requiere truncamiento."""
    lam = np.asarray(lam_total, dtype=float)
    return 1.0 - np.exp(-lam) * (1.0 + lam + lam**2 / 2.0)

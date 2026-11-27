"""Matemática de cuotas decimales. Funciones puras y vectorizadas (NumPy).

Convenciones (CLAUDE.md §4):
  p_imp = 1/Q                          umbral de equilibrio, no probabilidad verdadera
  overround = sum_i 1/Q_i - 1          SOLO sobre un mercado completo de una misma casa y momento
  proporcional: p_i = (1/Q_i) / sum_j (1/Q_j)
  potencia:     p_i = (1/Q_i)^k  con k tal que sum_i (1/Q_i)^k = 1
  EV = p*Q - 1                         binario, sin devolución; NO descontar el margen otra vez
  CLV = Q_obtenida / Q_cierre - 1
"""
from __future__ import annotations

import numpy as np

MIN_VALID_ODDS = 1.01


def implied_probability(q):
    q = np.asarray(q, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(q > 0, 1.0 / q, np.nan)


def overround(*qs):
    """Overround de un mercado completo: cada argumento es un vector de cuotas de un resultado."""
    if len(qs) < 2:
        raise ValueError("Se requieren todos los resultados del mercado (>= 2).")
    return np.sum([implied_probability(q) for q in qs], axis=0) - 1.0


def valid_odds(q, min_odds: float = MIN_VALID_ODDS):
    q = np.asarray(q, dtype=float)
    return np.isfinite(q) & (q >= min_odds)


def normalize_proportional(*qs):
    """Probabilidades sin margen por normalización proporcional. Devuelve una lista."""
    inv = [implied_probability(q) for q in qs]
    tot = np.sum(inv, axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        return [i / tot for i in inv]


def normalize_power(*qs, tol: float = 1e-12, max_iter: int = 200):
    """Método de potencia (Clarke et al. 2017): p_i = (1/Q_i)^k, sum p_i = 1.
    Bisección vectorizada sobre k en (0, 50]. Requiere overround > 0 (k > 1)
    o < 0 (k < 1); si overround = 0, k = 1."""
    inv = np.array([implied_probability(q) for q in qs], dtype=float)  # (m, n)
    n = inv.shape[1] if inv.ndim == 2 else 1
    inv = inv.reshape(len(qs), n)
    lo = np.full(n, 1e-6)
    hi = np.full(n, 50.0)
    ok = np.all(np.isfinite(inv), axis=0) & np.all(inv > 0, axis=0) & np.all(inv < 1, axis=0)
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        s = np.sum(inv ** mid, axis=0)
        # s decrece con k (inv < 1): si s > 1, k debe crecer
        lo = np.where(s > 1, mid, lo)
        hi = np.where(s > 1, hi, mid)
        if np.nanmax(hi - lo) < tol:
            break
    k = 0.5 * (lo + hi)
    out = inv ** k
    out[:, ~ok] = np.nan
    return [out[i] for i in range(len(qs))]


def expected_value(p, q):
    """EV por unidad apostada en un mercado binario sin devolución."""
    return np.asarray(p, dtype=float) * np.asarray(q, dtype=float) - 1.0


def closing_line_value(q_taken, q_close):
    return np.asarray(q_taken, dtype=float) / np.asarray(q_close, dtype=float) - 1.0


def logit(p):
    p = np.asarray(p, dtype=float)
    return np.log(p / (1 - p))


def inv_logit(x):
    return 1.0 / (1.0 + np.exp(-np.asarray(x, dtype=float)))

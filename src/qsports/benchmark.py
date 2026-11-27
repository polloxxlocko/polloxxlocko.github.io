"""Benchmarks de mercado y elementales para Over/Under 2,5 (ver MARKET_BENCHMARK_SPECIFICATION.md).

Principios:
- La probabilidad sin margen se calcula SOLO a partir de un par Over/Under de la MISMA
  casa (o del mismo agregado de la fuente) y del MISMO momento de observación.
- El par de máximos ('max') combina casas distintas: NUNCA se usa para probabilidades
  justas ni para estimar el margen de un operador; solo como mejor precio disponible.
- Las reglas de confiabilidad por fuente/período (configs/source_reliability.json)
  enmascaran solo las cuotas afectadas; nunca eliminan partidos completos.
- Bet365 no es una verdad objetiva: es una casa individual más.

Referencias:
  A  (principal)   pre-cierre: consenso = par promedio de la fuente normalizado (proporcional)
  A' (por casa)    pre-cierre: Bet365, Pinnacle (si confiable)
  A* (alternativo) media de probabilidades justas de casas individuales confiables
  B  (secundario)  cierre: promedio y por casa. SOLO referencia retrospectiva.
  C  (elemental)   frecuencia histórica de Over 2,5 por división con corte point-in-time
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import odds, paths

SINGLE_BOOK_PAIRS = {"pre": ["ou_pre_b365", "ou_pre_pin", "ou_pre_gb"], "close": ["ou_close_b365", "ou_close_pin"]}
CONSENSUS_PAIR = {"pre": "ou_pre_avg", "close": "ou_close_avg"}
BEST_PRICE_PAIR = {"pre": "ou_pre_max", "close": "ou_close_max"}
OVERROUND_RANGE = (0.0, 0.25)


def reliability_rules() -> list[dict]:
    return json.loads((paths.CONFIGS / "source_reliability.json").read_text())["rules"]


def apply_reliability(df: pd.DataFrame) -> pd.DataFrame:
    """Añade columnas '<prefijo>reliable' (bool) según reglas por fuente y período."""
    out = df.copy()
    prefixes = sorted({p for r in reliability_rules() for p in r["column_prefixes"]})
    for p in prefixes:
        out[f"{p}reliable"] = True
    for r in reliability_rules():
        start = pd.Timestamp(r["unreliable_from"]) if r["unreliable_from"] else pd.Timestamp.min
        end = pd.Timestamp(r["unreliable_to"]) if r["unreliable_to"] else pd.Timestamp.max
        bad = out["match_date"].between(start, end)
        for p in r["column_prefixes"]:
            out.loc[bad, f"{p}reliable"] = False
    return out


def pair_fair(df: pd.DataFrame, prefix: str, method: str = "proportional",
              require_reliable: bool = True) -> pd.DataFrame:
    """Probabilidad justa de Over para un par (misma casa/agregado y momento).
    Devuelve columnas: p_over, overround, valid, invalid_reason."""
    o = df.get(f"{prefix}_over", pd.Series(np.nan, index=df.index)).astype(float)
    u = df.get(f"{prefix}_under", pd.Series(np.nan, index=df.index)).astype(float)
    present = o.notna() & u.notna()
    ok_odds = present & odds.valid_odds(o) & odds.valid_odds(u)
    ov = pd.Series(odds.overround(o.values, u.values), index=df.index)
    in_range = ov.between(*OVERROUND_RANGE)
    rel_col = f"{prefix}_reliable"
    reliable = df[rel_col].astype(bool) if (require_reliable and rel_col in df.columns) else pd.Series(True, index=df.index)
    valid = ok_odds & in_range & reliable
    if method == "proportional":
        p = odds.normalize_proportional(o.values, u.values)[0]
    elif method == "power":
        p = odds.normalize_power(o.values, u.values)[0]
    else:
        raise ValueError(method)
    reason = np.select([~present, ~ok_odds, ~in_range, ~reliable], ["missing", "odds<1.01", "overround_out_of_range",
                                                                    "source_unreliable"], default="")
    return pd.DataFrame({"p_over": np.where(valid, p, np.nan), "overround": np.where(ok_odds, ov, np.nan),
                         "valid": valid.values, "invalid_reason": reason}, index=df.index)


def market_benchmarks(df: pd.DataFrame, method: str = "proportional") -> pd.DataFrame:
    """Calcula benchmarks A, A', A*, B y el mejor precio. No usa resultados."""
    d = apply_reliability(df)
    out = pd.DataFrame(index=d.index)
    out["match_id"] = d["match_id"]
    for when in ("pre", "close"):
        c = pair_fair(d, CONSENSUS_PAIR[when], method)
        tag = "A" if when == "pre" else "B"
        out[f"p_{tag}_consensus"] = c["p_over"]
        out[f"{tag}_consensus_overround"] = c["overround"]
        out[f"{tag}_consensus_valid"] = c["valid"]
        out[f"{tag}_consensus_invalid_reason"] = c["invalid_reason"]
        books = []
        for pref in SINGLE_BOOK_PAIRS[when]:
            if f"{pref}_over" not in d.columns:
                continue
            b = pair_fair(d, pref, method)
            name = pref.split("_")[-1]
            out[f"p_{tag}_{name}"] = b["p_over"]
            out[f"{tag}_{name}_overround"] = b["overround"]
            out[f"{tag}_{name}_valid"] = b["valid"]
            books.append(b["p_over"])
        # A*/B*: media de casas individuales válidas (consenso alternativo predefinido)
        stack = np.vstack([b.values for b in books]) if books else np.full((1, len(d)), np.nan)
        n = np.sum(np.isfinite(stack), axis=0)
        total = np.nansum(stack, axis=0)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[f"p_{tag}star_books_mean"] = np.where(n > 0, total / np.maximum(n, 1), np.nan)
        out[f"{tag}star_n_books"] = n
        out[f"{tag}star_valid"] = n > 0
        # mejor precio (combina casas): solo para EV/precio, nunca prob. justa
        bp = BEST_PRICE_PAIR[when]
        out[f"best_price_{when}_over"] = d.get(f"{bp}_over")
        out[f"best_price_{when}_under"] = d.get(f"{bp}_under")
    out["A_consensus_source"] = d.get("ou_pre_avg_source")
    return out


def common_sample(bench: pd.DataFrame, required: list[str]) -> pd.Series:
    """Máscara de filas donde TODOS los benchmarks requeridos son válidos (muestras idénticas)."""
    m = pd.Series(True, index=bench.index)
    for r in required:
        col = r if r.endswith("_valid") else f"{r}_valid"
        m &= bench[col].astype(bool)
    return m


def historical_frequency(df: pd.DataFrame, prior_a: float = 1.0, prior_b: float = 1.0,
                         group: str = "div") -> pd.Series:
    """Benchmark C: frecuencia histórica de Over 2,5 por división, point-in-time.
    Para cada partido usa SOLO partidos de la misma división con match_date < info_cutoff_date
    (ventana expansiva). Estimador (k + a) / (n + a + b); con a = b = 1 (Laplace) por defecto.
    Requiere columnas: match_date, info_cutoff_date, over25, y la columna de grupo."""
    res = pd.Series(np.nan, index=df.index, dtype=float)
    for g, sub in df.groupby(group, sort=False):
        hist = sub.loc[sub["over25"].notna(), ["match_date", "over25"]]
        daily = hist.groupby("match_date")["over25"].agg(["sum", "count"]).sort_index()
        dates = daily.index.values
        cs_k = np.concatenate([[0.0], daily["sum"].cumsum().values])
        cs_n = np.concatenate([[0.0], daily["count"].cumsum().values])
        # nº de días con fecha < cutoff
        cut = pd.to_datetime(sub["info_cutoff_date"])
        has_cut = cut.notna().values
        idx = np.searchsorted(dates, cut.fillna(pd.Timestamp.min).values, side="left")
        k, n = cs_k[idx], cs_n[idx]
        res.loc[sub.index] = np.where(has_cut, (k + prior_a) / (n + prior_a + prior_b), np.nan)
    return res

"""Validación de entradas del evaluador y de las uniones de predicciones (GATE 2.1, exigencia 3).

Política (EXPERIMENTAL_PROTOCOL.md §4.1):
- Probabilidades: finitas y en [0, 1]. Fuera de rango, ±inf o NaN -> InputValidationError.
- Resultados: exactamente 0 o 1 (finitos). Cualquier otro valor -> error.
- Dimensiones: todos los vectores de una evaluación tienen la misma longitud (> 0).
- Faltantes: el evaluador NO elimina filas. Cada comparación define primero su universo
  explícito (temporadas, máscara de elegibilidad, resultado conocido). Toda predicción debe
  existir y ser finita en cada fila del universo; si falta alguna, la comparación falla
  (no hay imputación ni descarte silencioso). Las filas fuera del universo se ignoran por
  definición y se cuentan en el informe de cobertura.
- Identificadores: `match_id` único en cada tabla de predicciones (por configuración y bloque)
  y en el marco de datos. Las uniones son 1:1 (`validate="one_to_one"`); nunca `pivot_table`
  (que agregaría duplicados en silencio).
- Cobertura: se compara el conjunto de `match_id` predichos con el universo esperado
  (faltantes y sobrantes).
"""
from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


class InputValidationError(ValueError):
    """Entrada inválida para el evaluador o para una unión de predicciones."""


def probabilities(p, name: str = "p") -> np.ndarray:
    a = np.asarray(p, dtype=float)
    if a.ndim != 1:
        raise InputValidationError(f"{name}: se espera un vector 1-D (forma {a.shape})")
    if a.size == 0:
        raise InputValidationError(f"{name}: vector vacío")
    nan = np.isnan(a)
    if nan.any():
        raise InputValidationError(f"{name}: {int(nan.sum())} valores faltantes (NaN); la política es fallar, "
                                   f"no descartar (defina el universo de la comparación antes de evaluar)")
    inf = np.isinf(a)
    if inf.any():
        raise InputValidationError(f"{name}: {int(inf.sum())} valores infinitos")
    bad = (a < 0) | (a > 1)
    if bad.any():
        raise InputValidationError(f"{name}: {int(bad.sum())} probabilidades fuera de [0, 1] "
                                   f"(mín {a.min():.6g}, máx {a.max():.6g})")
    return a


def outcomes(y, name: str = "y") -> np.ndarray:
    a = np.asarray(y, dtype=float)
    if a.ndim != 1:
        raise InputValidationError(f"{name}: se espera un vector 1-D (forma {a.shape})")
    if a.size == 0:
        raise InputValidationError(f"{name}: vector vacío")
    if not np.isfinite(a).all():
        raise InputValidationError(f"{name}: {int((~np.isfinite(a)).sum())} resultados faltantes o infinitos")
    if not np.isin(a, (0.0, 1.0)).all():
        raise InputValidationError(f"{name}: resultados no binarios {sorted(set(a[~np.isin(a, (0.0, 1.0))]))[:5]}")
    return a


def same_length(**arrays) -> int:
    lens = {k: len(v) for k, v in arrays.items()}
    if len(set(lens.values())) != 1:
        raise InputValidationError(f"Dimensiones distintas: {lens}")
    return next(iter(lens.values()))


def dates(d, name: str = "dates") -> pd.Series:
    s = pd.to_datetime(pd.Series(d).reset_index(drop=True), errors="coerce")
    if s.isna().any():
        raise InputValidationError(f"{name}: {int(s.isna().sum())} fechas faltantes o inválidas")
    return s


def unique_ids(df: pd.DataFrame, col: str = "match_id", context: str = "") -> None:
    if col not in df.columns:
        raise InputValidationError(f"[{context}] falta la columna {col}")
    if df[col].isna().any():
        raise InputValidationError(f"[{context}] {int(df[col].isna().sum())} {col} faltantes")
    dup = df[col].duplicated(keep=False)
    if dup.any():
        ex = df.loc[dup, col].unique()[:3].tolist()
        raise InputValidationError(f"[{context}] {int(dup.sum())} filas con {col} duplicado (p. ej. {ex})")


def merge_one_to_one(left: pd.DataFrame, right: pd.DataFrame, on: str = "match_id", how: str = "left",
                     context: str = "") -> pd.DataFrame:
    """Unión 1:1 verificada (ambos lados con clave única)."""
    unique_ids(left, on, f"{context}:izquierda")
    unique_ids(right, on, f"{context}:derecha")
    out = left.merge(right, on=on, how=how, validate="one_to_one")
    if how == "left" and len(out) != len(left):
        raise InputValidationError(f"[{context}] la unión cambió el número de filas")
    return out


def coverage(pred_ids: Iterable, expected_ids: Iterable, context: str = "") -> dict:
    """Cobertura de un conjunto de predicciones respecto del universo esperado."""
    p, e = pd.Index(pd.unique(pd.Series(list(pred_ids)))), pd.Index(pd.unique(pd.Series(list(expected_ids))))
    missing, extra = e.difference(p), p.difference(e)
    return {"context": context, "expected": int(len(e)), "predicted": int(len(p)), "covered": int(len(e) - len(missing)),
            "missing": int(len(missing)), "extra": int(len(extra)),
            "coverage": float((len(e) - len(missing)) / len(e)) if len(e) else float("nan")}


def require_full_coverage(pred: pd.DataFrame, universe: pd.DataFrame, context: str,
                          value_col: str = "p_over") -> dict:
    """Exige una predicción finita para cada fila del universo (falla si falta alguna)."""
    unique_ids(pred, "match_id", context)
    unique_ids(universe, "match_id", f"{context}:universo")
    cov = coverage(pred["match_id"], universe["match_id"], context)
    if cov["missing"]:
        raise InputValidationError(f"[{context}] faltan predicciones para {cov['missing']} de {cov['expected']} "
                                   f"filas del universo")
    vals = universe[["match_id"]].merge(pred[["match_id", value_col]], on="match_id", how="left",
                                        validate="one_to_one")[value_col]
    if vals.isna().any():
        raise InputValidationError(f"[{context}] {int(vals.isna().sum())} predicciones NaN dentro del universo")
    probabilities(vals.to_numpy(), f"{context}:{value_col}")
    return cov

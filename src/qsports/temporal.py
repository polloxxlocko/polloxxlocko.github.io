"""Arquitectura temporal point-in-time.

Fuentes (verificadas el 2026-11-27):
- matches.php: "odds are collected for the downloadable weekend fixtures on Fridays
  afternoons generally not later than 17:00 British Standard Time. Odds for midweek
  fixtures are collected Tuesdays not later than 13:00 British Standard Time."
- notes.txt: "Betting odds for weekend games are collected Friday afternoons, and on
  Tuesday afternoons for midweek games." Cierre = últimas cuotas antes del inicio.
- Time: hora de inicio en hora del Reino Unido (verificación empírica: sábados de
  Bundesliga 14:30 = 15:30 CET; Serie A 19:45 = 20:45 CET). Disponible desde 2019/20.

Lo que NO existe en los datos: timestamp por fila de la captura pre-cierre. La fecha de
captura es una ESTIMACIÓN por regla; su precisión se registra como 'rule_based_date'.

Regla de asignación (supuesto documentado, aplicado también a temporadas antiguas):
  partido en Vie, Sáb, Dom, Lun -> captura el viernes previo o del mismo día (<= 17:00 UK)
  partido en Mar, Mié, Jue      -> captura el martes de esa semana (<= 13:00 UK)

Corte de información (conservador): para predecir un partido solo pueden usarse
resultados de partidos con fecha ESTRICTAMENTE ANTERIOR a la fecha de captura estimada.
Esto (a) excluye siempre resultados del mismo día, cuyo orden no es determinable, y
(b) evita que el modelo tenga más información que la cuota pre-cierre de referencia.

Ambigüedad: si se conoce la hora y el partido empieza ANTES del límite de captura
(viernes < 17:00 o martes < 13:00 UK), la cuota pudo capturarse en otro momento
(p. ej., en la captura anterior). Esos partidos se marcan y se excluyen de las
comparaciones primarias con el mercado (configs/exclusion_criteria.json).
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

UK = ZoneInfo("Europe/London")
UTC = ZoneInfo("UTC")
FRIDAY, TUESDAY = 4, 1  # Monday = 0
CAPTURE_DEADLINE = {"weekend_friday": dt.time(17, 0), "midweek_tuesday": dt.time(13, 0)}


def capture_date_for(match_date: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Fecha estimada de captura pre-cierre y regla aplicada (vectorizado)."""
    d = pd.to_datetime(match_date)
    wd = d.dt.weekday
    # días a restar: Vie 0, Sáb 1, Dom 2, Lun 3 | Mar 0, Mié 1, Jue 2
    back = pd.Series(np.select(
        [wd == 4, wd == 5, wd == 6, wd == 0, wd == 1, wd == 2, wd == 3],
        [0, 1, 2, 3, 0, 1, 2], default=-1), index=d.index)
    rule = pd.Series(np.where(wd.isin([4, 5, 6, 0]), "weekend_friday",
                              np.where(wd.isin([1, 2, 3]), "midweek_tuesday", None)), index=d.index)
    cap = d - pd.to_timedelta(back.where(back >= 0), unit="D")
    cap = cap.where(d.notna())
    return cap, rule


def parse_kickoff(match_date: pd.Series, time_uk: pd.Series) -> tuple[pd.Series, pd.Series]:
    """kickoff_at_utc (tz-aware) y precisión ('minute' si hay hora, 'date' si no)."""
    t = time_uk.astype("string").str.strip()
    ok = t.str.fullmatch(r"\d{1,2}:\d{2}").fillna(False)
    local = pd.to_datetime(match_date.dt.strftime("%Y-%m-%d") + " " + t.where(ok, "00:00"),
                           format="%Y-%m-%d %H:%M", errors="coerce")
    local = local.where(ok.astype(bool))
    loc = local.dt.tz_localize(UK, ambiguous="NaT", nonexistent="NaT")
    kick_utc = loc.dt.tz_convert(UTC)
    precision = pd.Series(np.where(kick_utc.notna(), "minute", "date"), index=match_date.index)
    return kick_utc, precision


def add_temporal_fields(df: pd.DataFrame, retrieved_at_utc: dict[str, str] | None = None) -> pd.DataFrame:
    """Añade los campos temporales canónicos a un DataFrame de partidos canónicos."""
    out = df.copy()
    out["weekday"] = out["match_date"].dt.weekday
    out["kickoff_at_utc"], out["kickoff_precision"] = parse_kickoff(out["match_date"], out["kickoff_time_uk"])
    cap, rule = capture_date_for(out["match_date"])
    out["pre_odds_capture_date_est"] = cap
    out["pre_odds_capture_rule"] = rule
    out["pre_odds_capture_precision"] = "rule_based_date"
    deadline = pd.Series([CAPTURE_DEADLINE.get(r) if isinstance(r, str) else None for r in rule], index=out.index)
    out["pre_odds_capture_deadline_uk"] = pd.Series(
        [None if (pd.isna(c) or d is None) else dt.datetime.combine(c.date(), d).strftime("%Y-%m-%d %H:%M")
         for c, d in zip(cap, deadline)], index=out.index, dtype="string")
    # ambigüedad: hora conocida y anterior al límite de captura del mismo día
    t = out["kickoff_time_uk"].astype("string")
    ok = t.str.fullmatch(r"\d{1,2}:\d{2}").fillna(False).astype(bool)
    hhmm = pd.to_datetime(t.where(ok), format="%H:%M", errors="coerce").dt.time
    amb_fri = (out["weekday"] == FRIDAY) & ok & pd.Series([h is not None and not pd.isna(h) and h < dt.time(17, 0)
                                                           for h in hhmm], index=out.index)
    amb_tue = (out["weekday"] == TUESDAY) & ok & pd.Series([h is not None and not pd.isna(h) and h < dt.time(13, 0)
                                                            for h in hhmm], index=out.index)
    out["capture_rule_ambiguous"] = (amb_fri | amb_tue).astype(bool)
    out["capture_time_unverifiable"] = (out["weekday"].isin([FRIDAY, TUESDAY]) & ~ok).astype(bool)
    # corte de información: usar solo resultados con match_date < info_cutoff_date
    out["info_cutoff_date"] = cap
    out["close_odds_capture"] = "aprox_inicio_partido"
    out["result_available_date"] = out["match_date"]  # resultado conocido al terminar ese día
    if retrieved_at_utc is not None:
        out["dataset_retrieved_at_utc"] = out["season_code"].map(retrieved_at_utc)
    return out


def history_mask(history_dates: pd.Series, cutoff_date: pd.Timestamp) -> pd.Series:
    """Filas de historia utilizables para una predicción con fecha de corte dada."""
    return pd.to_datetime(history_dates) < pd.Timestamp(cutoff_date)

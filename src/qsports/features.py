"""Variables point-in-time por equipo (EWMA) para M3/M4.

Garantía: la variable de un partido usa solo partidos del equipo con
match_date < info_cutoff_date de ese partido (merge_asof con allow_exact_matches=False).
Identidad de equipo = país|nombre canónico (la historia sigue al equipo entre divisiones).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

STAT_PAIRS = {"g": ("fthg", "ftag"), "s": ("hs", "as_"), "t": ("hst", "ast"), "c": ("hc", "ac")}
FEATURE_GROUPS = {"G": ["g"], "GS": ["g", "s"], "GST": ["g", "s", "t"], "GSTC": ["g", "s", "t", "c"]}


def _long(df: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for side, opp in (("home", "away"), ("away", "home")):
        p = pd.DataFrame({"team_id": df["country"].astype(str) + "|" + df[f"{side}_team"].astype(str),
                          "date": df["match_date"].values, "match_id": df["match_id"].values})
        for k, (hc, ac) in STAT_PAIRS.items():
            f, a = (hc, ac) if side == "home" else (ac, hc)
            p[f"{k}_for"] = df[f].values
            p[f"{k}_against"] = df[a].values
        parts.append(p)
    return pd.concat(parts, ignore_index=True)


def team_states(df: pd.DataFrame, half_life_matches: float) -> pd.DataFrame:
    """Estado EWMA de cada equipo DESPUÉS de cada uno de sus partidos (clave: fecha del partido)."""
    L = _long(df).dropna(subset=["date"]).sort_values(["team_id", "date", "match_id"], kind="mergesort")
    alpha = 1 - 0.5 ** (1 / half_life_matches)
    cols = [c for c in L.columns if c.endswith(("_for", "_against"))]
    ew = L.groupby("team_id", sort=False)[cols].transform(lambda s: s.ewm(alpha=alpha, ignore_na=True).mean())
    st = pd.concat([L[["team_id", "date"]], ew], axis=1)
    st["n_prior"] = L.groupby("team_id", sort=False).cumcount() + 1
    st["last_date"] = st["date"]
    # un solo estado por equipo y fecha (el último del día)
    st = st.groupby(["team_id", "date"], sort=False).tail(1)
    return st.sort_values("date", kind="mergesort").reset_index(drop=True)


def build_features(df: pd.DataFrame, half_life_matches: float = 10.0) -> pd.DataFrame:
    """Variables feat_* alineadas con df.index, calculadas solo con partidos < info_cutoff_date."""
    st = team_states(df, half_life_matches)
    out = pd.DataFrame(index=df.index)
    for side in ("home", "away"):
        q = pd.DataFrame({"team_id": df["country"].astype(str) + "|" + df[f"{side}_team"].astype(str),
                          "cutoff": pd.to_datetime(df["info_cutoff_date"]), "_row": df.index})
        has = q["cutoff"].notna()
        qs = q[has].sort_values("cutoff", kind="mergesort")
        m = pd.merge_asof(qs, st, left_on="cutoff", right_on="date", by="team_id",
                          direction="backward", allow_exact_matches=False)
        m = m.set_index("_row").reindex(df.index)
        s = side[0]
        for c in [c for c in st.columns if c.endswith(("_for", "_against"))]:
            out[f"feat_{s}_{c}"] = m[c].astype(float)
        out[f"feat_{s}_n_prior"] = m["n_prior"].fillna(0).astype(float)
        out[f"feat_{s}_rest_days"] = (pd.to_datetime(df["match_date"]) - m["last_date"]).dt.days.astype(float)
    return out


def feature_columns(group: str) -> list[str]:
    cols = []
    for s in ("h", "a"):
        for k in FEATURE_GROUPS[group]:
            cols += [f"feat_{s}_{k}_for", f"feat_{s}_{k}_against"]
        cols += [f"feat_{s}_n_prior"]
    return cols

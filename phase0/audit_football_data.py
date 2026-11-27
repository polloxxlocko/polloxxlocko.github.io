"""Fase Cero — auditoría empírica de Football-Data.co.uk (capa RAW).

Mide, por temporada y división:
  * nº de partidos y filas no parseables;
  * cobertura de cuotas 1X2 y Over/Under 2,5 (pre-cierre y cierre) por fuente;
  * cobertura de estadísticas (córners, tarjetas, árbitro, tiros, xG, hora);
  * márgenes (overround) de mercados COMPLETOS (1X2: tres resultados; O/U: dos);
  * comprobaciones de integridad (cuotas < 1.01, duplicados, FTR incoherente);
  * coherencia de Pinnacle frente a Bet365 antes/después del 23/07/2025
    (advertencia publicada por Football-Data).

SALVAGUARDA DE PRUEBA FINAL (propuesta, ver CLAUDE.md):
  Las estadísticas que dependen del RESULTADO (tasa de Over 2,5, Brier del mercado)
  se calculan solo para temporadas <= SEALED_FROM - 1. Las temporadas >= SEALED_FROM
  se usan únicamente para cobertura y márgenes (no usan resultados).

No entrena modelos ni evalúa estrategias de apuesta.

Uso:  python phase0/audit_football_data.py
"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "football_data"
OUT = ROOT / "reports" / "phase0"
SEALED_FROM = "2425"          # temporadas >= 2024/25: resultados no examinados
PINNACLE_WARNING_DATE = pd.Timestamp("2025-07-23")

OU_PRE = {  # fuente -> (over, under)
    "B365": ("B365>2.5", "B365<2.5"),
    "PIN": ("P>2.5", "P<2.5"),
    "AVG": ("Avg>2.5", "Avg<2.5"),
    "BbAV": ("BbAv>2.5", "BbAv<2.5"),
    "MAX": ("Max>2.5", "Max<2.5"),
    "BbMX": ("BbMx>2.5", "BbMx<2.5"),
}
OU_CLOSE = {
    "B365C": ("B365C>2.5", "B365C<2.5"),
    "PINC": ("PC>2.5", "PC<2.5"),
    "AVGC": ("AvgC>2.5", "AvgC<2.5"),
    "MAXC": ("MaxC>2.5", "MaxC<2.5"),
}
X12_PRE = {
    "B365": ("B365H", "B365D", "B365A"),
    "PIN": ("PSH", "PSD", "PSA"),
    "AVG": ("AvgH", "AvgD", "AvgA"),
    "BbAV": ("BbAvH", "BbAvD", "BbAvA"),
}
X12_CLOSE = {
    "B365C": ("B365CH", "B365CD", "B365CA"),
    "PINC": ("PSCH", "PSCD", "PSCA"),
    "AVGC": ("AvgCH", "AvgCD", "AvgCA"),
}
STATS = {
    "time": ["Time"],
    "corners": ["HC", "AC"],
    "yellow": ["HY", "AY"],
    "red": ["HR", "AR"],
    "referee": ["Referee"],
    "shots": ["HS", "AS"],
    "shots_target": ["HST", "AST"],
    "xg": ["HxG", "AxG"],
}


def read_zip(zpath: Path) -> list[tuple[str, pd.DataFrame, int]]:
    out = []
    with zipfile.ZipFile(zpath) as z:
        for name in sorted(z.namelist()):
            if not name.endswith(".csv"):
                continue
            raw = z.read(name).decode("latin-1")
            # Algunas filas antiguas (2001-2008) traen más campos que la cabecera: se
            # agregaron casas a mitad de temporada. Los campos iniciales siguen alineados,
            # así que se rellena la cabecera con columnas '_extraN' en vez de descartar filas.
            lines = raw.splitlines()
            header = [h.strip() for h in lines[0].split(",")]
            maxf = max(l.count(",") + 1 for l in lines if l.strip())
            n_wide = sum(1 for l in lines[1:] if l.strip() and l.count(",") + 1 > len(header))
            names = header + [f"_extra{i}" for i in range(maxf - len(header))]
            names = [n if n else f"_blank{i}" for i, n in enumerate(names)]
            seen: dict[str, int] = {}
            for i, n in enumerate(names):  # cabeceras con nombres repetidos -> sufijo .k
                if n in seen:
                    seen[n] += 1
                    names[i] = f"{n}.{seen[n]}"
                else:
                    seen[n] = 0
            df = pd.read_csv(io.StringIO("\n".join(lines[1:])), header=None, names=names,
                             engine="python", dtype=str)
            df = df.dropna(how="all")
            df = df.rename(columns={"HT": "HomeTeam", "AT": "AwayTeam"})
            out.append((name[:-4], df, n_wide))
    return out


def num(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(np.nan, index=df.index)
    return pd.to_numeric(df[col], errors="coerce")


def has_all(df: pd.DataFrame, cols) -> pd.Series:
    ok = pd.Series(True, index=df.index)
    for c in cols:
        ok &= num(df, c).ge(1.01) if c not in ("Referee", "Time") else (
            df[c].notna() & df[c].astype(str).str.strip().ne("") if c in df.columns
            else pd.Series(False, index=df.index))
    return ok


def stat_present(df, cols):
    ok = pd.Series(True, index=df.index)
    for c in cols:
        if c not in df.columns:
            return pd.Series(False, index=df.index)
        if c in ("Referee", "Time"):
            ok &= df[c].notna() & df[c].astype(str).str.strip().ne("")
        else:
            ok &= pd.to_numeric(df[c], errors="coerce").notna()
    return ok


def overround(df, cols):
    inv = sum(1.0 / num(df, c) for c in cols)
    return inv - 1.0


def fair_over(df, oc, uc):
    io_, iu = 1 / num(df, oc), 1 / num(df, uc)
    return io_ / (io_ + iu)


def parse_dates(s: pd.Series) -> pd.Series:
    d = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
    d2 = pd.to_datetime(s, format="%d/%m/%y", errors="coerce")
    return d.fillna(d2)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows, pin_rows, base_rows = [], [], []
    for zpath in sorted(RAW.glob("*/data.zip")):
        season = zpath.parent.name
        for div, df, nbad in read_zip(zpath):
            df = df[num(df, "FTHG").notna() & num(df, "FTAG").notna()].copy()
            n = len(df)
            if n == 0:
                continue
            r = {"season": season, "div": div, "n_matches": n, "rows_wider_than_header_recovered": nbad}
            for k, (o, u) in {**OU_PRE, **OU_CLOSE}.items():
                m = has_all(df, (o, u))
                r[f"ou_{k}"] = m.mean()
                if m.any():
                    r[f"ou_{k}_overround_med"] = overround(df[m], (o, u)).median()
            for k, cols in {**X12_PRE, **X12_CLOSE}.items():
                m = has_all(df, cols)
                r[f"x12_{k}"] = m.mean()
                if m.any():
                    r[f"x12_{k}_overround_med"] = overround(df[m], cols).median()
            for k, cols in STATS.items():
                r[f"stat_{k}"] = stat_present(df, cols).mean()
            # Integridad
            odd_cols = [c for v in {**OU_PRE, **OU_CLOSE, **X12_PRE, **X12_CLOSE}.values() for c in v
                        if c in df.columns]
            vals = pd.concat([num(df, c) for c in odd_cols], axis=1) if odd_cols else pd.DataFrame()
            r["odds_below_1.01"] = int(((vals < 1.01) & vals.notna()).sum().sum()) if len(vals.columns) else 0
            dates = parse_dates(df["Date"]) if "Date" in df.columns else pd.Series(pd.NaT, index=df.index)
            r["date_unparsed"] = int(dates.isna().sum())
            key = pd.DataFrame({"d": dates, "h": df.get("HomeTeam"), "a": df.get("AwayTeam")})
            r["duplicates"] = int(key.duplicated().sum())
            if "FTR" in df.columns:
                hg, ag = num(df, "FTHG"), num(df, "FTAG")
                exp = np.where(hg > ag, "H", np.where(hg < ag, "A", "D"))
                r["ftr_inconsistent"] = int((df["FTR"].astype(str).str.strip() != exp).sum())
            # Implausible overround in O/U closing B365 (fuera de [-2%, 20%])
            for k, (o, u) in (("B365C", OU_CLOSE["B365C"]), ("AVGC", OU_CLOSE["AVGC"])):
                m = has_all(df, (o, u))
                if m.any():
                    ov = overround(df[m], (o, u))
                    r[f"ou_{k}_overround_out_of_range"] = int(((ov < -0.02) | (ov > 0.20)).sum())
            rows.append(r)

            # Pinnacle vs Bet365 (solo cuotas, sin resultados)
            for tag, (po, pu), (bo, bu) in (
                ("pre", OU_PRE["PIN"], OU_PRE["B365"]),
                ("close", OU_CLOSE["PINC"], OU_CLOSE["B365C"]),
            ):
                m = has_all(df, (po, pu, bo, bu))
                if m.any():
                    d = df[m]
                    diff = (fair_over(d, po, pu) - fair_over(d, bo, bu)).abs()
                    pin_rows.append(pd.DataFrame({"date": dates[m], "kind": tag, "absdiff": diff.values,
                                                  "season": season, "div": div}))

            # Estadísticas dependientes del resultado: SOLO temporadas no selladas
            if season < SEALED_FROM:
                tot = num(df, "FTHG") + num(df, "FTAG")
                br = {"season": season, "div": div, "n": n, "over25_rate": (tot > 2.5).mean(),
                      "mean_goals": tot.mean(), "var_goals": tot.var(ddof=1)}
                for k, (o, u) in (("AVGC", OU_CLOSE["AVGC"]), ("B365C", OU_CLOSE["B365C"]),
                                  ("PINC", OU_CLOSE["PINC"]), ("BbAV", OU_PRE["BbAV"]),
                                  ("AVG", OU_PRE["AVG"])):
                    m = has_all(df, (o, u))
                    if m.sum() >= 30:
                        p = fair_over(df[m], o, u)
                        y = (tot[m] > 2.5).astype(float)
                        br[f"brier_{k}"] = float(((p - y) ** 2).mean())
                        br[f"n_{k}"] = int(m.sum())
                base_rows.append(br)

    cov = pd.DataFrame(rows).sort_values(["season", "div"])
    cov.to_csv(OUT / "football_data_coverage_by_season_div.csv", index=False)

    # Resumen por temporada (ponderado por partidos)
    pct_cols = [c for c in cov.columns if (c.startswith(("ou_", "x12_", "stat_"))
                                         and not c.endswith(("_med", "_range")))]
    w = cov["n_matches"]
    summ = cov.groupby("season").apply(
        lambda g: pd.Series({"divisions": g["div"].nunique(), "n_matches": g["n_matches"].sum(),
                             **{c: np.average(g[c].fillna(0), weights=g["n_matches"]) for c in pct_cols}}),
        include_groups=False)
    summ.to_csv(OUT / "football_data_coverage_by_season.csv")

    # Márgenes medianos por fuente (temporadas 2019/20+)
    rec = cov[cov["season"] >= "1920"]
    margins = {c: float(rec[c].median()) for c in rec.columns if c.endswith("_overround_med")}

    # Pinnacle: diferencia absoluta mensual vs Bet365 (prob. justa de Over)
    pin = pd.concat(pin_rows, ignore_index=True)
    pin["period"] = np.where(pin["date"] >= PINNACLE_WARNING_DATE, "post_2025-07-23", "pre_2025-07-23")
    recent = pin[pin["date"] >= pd.Timestamp("2023-07-01")]
    pin_summary = recent.groupby(["kind", "period"])["absdiff"].describe(percentiles=[.5, .9]).round(4)
    pin_summary.to_csv(OUT / "pinnacle_vs_b365_ou_fairprob_absdiff.csv")

    base = pd.DataFrame(base_rows)
    base.to_csv(OUT / "football_data_outcome_stats_unsealed.csv", index=False)

    totals = {
        "seasons": int(cov["season"].nunique()),
        "division_files": int(len(cov)),
        "matches_total": int(cov["n_matches"].sum()),
        "rows_wider_than_header_recovered_total": int(cov["rows_wider_than_header_recovered"].sum()),
        "odds_below_1.01_total": int(cov["odds_below_1.01"].sum()),
        "duplicates_total": int(cov["duplicates"].sum()),
        "ftr_inconsistent_total": int(cov.get("ftr_inconsistent", pd.Series(0)).fillna(0).sum()),
        "date_unparsed_total": int(cov["date_unparsed"].sum()),
        "matches_with_ou_closing_B365_and_AVG_since_1920": int(
            (rec["n_matches"] * np.minimum(rec["ou_B365C"].fillna(0), rec["ou_AVGC"].fillna(0))).sum()),
        "matches_with_any_ou_pre_odds": int((cov["n_matches"] * cov[["ou_B365", "ou_BbAV", "ou_AVG"]]
                                             .fillna(0).max(axis=1)).sum()),
        "median_overrounds_since_1920": margins,
        "sealed_from_season": SEALED_FROM,
        "unsealed_matches_for_outcome_stats": int(base["n"].sum()),
        "over25_rate_unsealed_weighted": float(np.average(base["over25_rate"], weights=base["n"])),
        "var_to_mean_goals_unsealed_median": float((base["var_goals"] / base["mean_goals"]).median()),
    }
    for k in ("AVGC", "B365C", "PINC", "BbAV"):
        sub = base.dropna(subset=[f"brier_{k}"])
        if len(sub):
            totals[f"brier_market_{k}_unsealed"] = float(np.average(sub[f"brier_{k}"], weights=sub[f"n_{k}"]))
            totals[f"brier_market_{k}_n"] = int(sub[f"n_{k}"].sum())
    sub = base.dropna(subset=["brier_AVGC"])
    if len(sub):
        rate = np.average(sub["over25_rate"], weights=sub["n"])
        totals["brier_climatology_same_rows_approx"] = float(rate * (1 - rate))
    (OUT / "football_data_audit_summary.json").write_text(json.dumps(totals, indent=2, ensure_ascii=False))
    print(json.dumps(totals, indent=2, ensure_ascii=False))
    print("\nPinnacle vs B365 (|p_over_justa_PIN - p_over_justa_B365|), desde 2023/24:\n", pin_summary)


if __name__ == "__main__":
    main()

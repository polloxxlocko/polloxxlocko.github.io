"""Ingesta de Football-Data.co.uk: descarga enrutada por partición y parser tolerante.

- La descarga escribe cada temporada en el directorio RAW de SU partición
  (dev / holdout / prospective). Los archivos RAW nunca se sobrescriben.
- El parser NO descarta filas: recupera filas con más campos que la cabecera,
  normaliza alias (HT/AT, HG/AG, Res, PH/PSH), desambigua cabeceras repetidas y
  detecta la codificación por archivo.
- Este módulo no conoce el contenido reservado: `iter_dev_zips` solo lista RAW de
  desarrollo. El acceso a RAW reservado ocurre únicamente dentro de `qsports.holdout`.

Nomenclatura: "pre" = cuota previa al cierre (capturada viernes/martes según la regla de
la fuente). NO es una cuota de apertura.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from . import paths
from .divisions import DIVISIONS

BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/data.zip"
USER_AGENT = "quantitative-sports-research/0.2 (non-commercial research; polite)"

# ---------------------------------------------------------------- columnas canónicas
ALIASES = {"HT": "HomeTeam", "AT": "AwayTeam", "HG": "FTHG", "AG": "FTAG", "Res": "FTR",
           "PH": "PSH", "PD": "PSD", "PA": "PSA"}

SIMPLE_MAP = {
    "Div": "div_raw", "Date": "date_raw", "Time": "kickoff_time_uk",
    "HomeTeam": "home_team", "AwayTeam": "away_team",
    "FTHG": "fthg", "FTAG": "ftag", "FTR": "ftr", "HTHG": "hthg", "HTAG": "htag", "HTR": "htr",
    "Referee": "referee", "Attendance": "attendance",
    "HS": "hs", "AS": "as_", "HST": "hst", "AST": "ast", "HC": "hc", "AC": "ac",
    "HF": "hf", "AF": "af", "HY": "hy", "AY": "ay", "HR": "hr", "AR": "ar",
    "HxG": "hxg", "AxG": "axg",
    # O/U 2,5 previas al cierre
    "B365>2.5": "ou_pre_b365_over", "B365<2.5": "ou_pre_b365_under",
    "P>2.5": "ou_pre_pin_over", "P<2.5": "ou_pre_pin_under",
    "GB>2.5": "ou_pre_gb_over", "GB<2.5": "ou_pre_gb_under",
    "BbOU": "ou_pre_n_books",
    # O/U 2,5 cierre
    "B365C>2.5": "ou_close_b365_over", "B365C<2.5": "ou_close_b365_under",
    "PC>2.5": "ou_close_pin_over", "PC<2.5": "ou_close_pin_under",
    "AvgC>2.5": "ou_close_avg_over", "AvgC<2.5": "ou_close_avg_under",
    "MaxC>2.5": "ou_close_max_over", "MaxC<2.5": "ou_close_max_under",
    # 1X2 (contexto / posibles predictores pre-partido)
    "B365H": "x12_pre_b365_h", "B365D": "x12_pre_b365_d", "B365A": "x12_pre_b365_a",
    "PSH": "x12_pre_pin_h", "PSD": "x12_pre_pin_d", "PSA": "x12_pre_pin_a",
    "B365CH": "x12_close_b365_h", "B365CD": "x12_close_b365_d", "B365CA": "x12_close_b365_a",
    "PSCH": "x12_close_pin_h", "PSCD": "x12_close_pin_d", "PSCA": "x12_close_pin_a",
    "AvgCH": "x12_close_avg_h", "AvgCD": "x12_close_avg_d", "AvgCA": "x12_close_avg_a",
}
# Columnas cuyo origen depende del régimen (Oddsportal 'Avg/Max' desde 2019/20; Betbrain 'Bb*' antes)
REGIME_MAP = {
    "ou_pre_avg_over": ("Avg>2.5", "BbAv>2.5"), "ou_pre_avg_under": ("Avg<2.5", "BbAv<2.5"),
    "ou_pre_max_over": ("Max>2.5", "BbMx>2.5"), "ou_pre_max_under": ("Max<2.5", "BbMx<2.5"),
    "x12_pre_avg_h": ("AvgH", "BbAvH"), "x12_pre_avg_d": ("AvgD", "BbAvD"), "x12_pre_avg_a": ("AvgA", "BbAvA"),
}
NUMERIC_PREFIXES = ("ou_", "x12_")
NUMERIC_STATS = ["fthg", "ftag", "hthg", "htag", "hs", "as_", "hst", "ast", "hc", "ac", "hf", "af",
                 "hy", "ay", "hr", "ar", "hxg", "axg", "attendance"]
OUTCOME_COLUMNS = ["fthg", "ftag", "ftr", "hthg", "htag", "htr", "total_goals", "over25"]
POSTMATCH_STAT_COLUMNS = ["hs", "as_", "hst", "ast", "hc", "ac", "hf", "af", "hy", "ay", "hr", "ar",
                          "hxg", "axg", "attendance", "referee"]


# ---------------------------------------------------------------- utilidades
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def season_codes(first: str, last: str) -> list[str]:
    a, b = int(first[:2]), int(last[:2])
    return [f"{y:02d}{(y + 1) % 100:02d}" for y in range(a, b + 1)]


def season_label(code: str) -> str:
    y = int(code[:2])
    return f"{2000 + y}/{(y + 1) % 100:02d}"


def make_match_id(div: str, date: pd.Series, home: pd.Series, away: pd.Series) -> pd.Series:
    key = div + "|" + date.dt.strftime("%Y-%m-%d").fillna("NaT") + "|" + home.fillna("") + "|" + away.fillna("")
    return key.map(lambda k: hashlib.sha1(k.encode("utf-8")).hexdigest()[:16])


_ALIASES_CACHE: dict | None = None


def team_aliases() -> dict:
    global _ALIASES_CACHE
    if _ALIASES_CACHE is None:
        _ALIASES_CACHE = json.loads((paths.CONFIGS / "team_aliases.json").read_text())["aliases"]
    return _ALIASES_CACHE


def decode_bytes(b: bytes) -> tuple[str, str]:
    """Detecta codificación por archivo: utf-8-sig -> cp1252 -> latin-1."""
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return b.decode(enc), enc
        except UnicodeDecodeError:
            continue
    raise ValueError("No decodificable")  # latin-1 nunca falla; inalcanzable


# ---------------------------------------------------------------- descarga
def download_seasons(codes: list[str], sleep: float = 2.0, session: requests.Session | None = None) -> list[dict]:
    """Descarga data.zip por temporada al RAW de su partición. No sobrescribe."""
    s = session or requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    out = []
    for code in codes:
        root = paths.raw_dir_for(code)
        dest = root / code / "data.zip"
        rec = {"source": "football-data.co.uk", "season_code": code, "partition": paths.partition_of(code),
               "url": BASE_URL.format(season=code)}
        if dest.exists():
            rec |= {"status": "exists_not_overwritten", "sha256": sha256_file(dest),
                    "checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
        else:
            r = s.get(rec["url"], timeout=120)
            rec |= {"http_status": r.status_code, "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "last_modified_header": r.headers.get("Last-Modified")}
            if r.status_code == 200 and r.content[:2] == b"PK":
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_suffix(".part")
                tmp.write_bytes(r.content)
                tmp.rename(dest)
                rec |= {"status": "downloaded", "bytes": dest.stat().st_size, "sha256": sha256_file(dest)}
            else:
                rec |= {"status": "failed"}
            time.sleep(sleep)
        root.mkdir(parents=True, exist_ok=True)
        with (root / "manifest.jsonl").open("a") as m:
            m.write(json.dumps(rec, ensure_ascii=False) + "\n")
        out.append(rec)
    return out


def iter_dev_zips() -> list[tuple[str, Path]]:
    """Archivos RAW de DESARROLLO (nunca reservados)."""
    out = []
    for z in sorted(paths.RAW_DEV.glob("*/data.zip")):
        code = z.parent.name
        if paths.partition_of(code) != "dev":
            raise RuntimeError(f"Temporada reservada {code} encontrada en RAW de desarrollo: {z}")
        out.append((code, z))
    return out


# ---------------------------------------------------------------- parser
def _read_csv_tolerant(text: str) -> tuple[pd.DataFrame, int, list[str]]:
    lines = [l for l in text.splitlines()]
    while lines and not lines[-1].strip():
        lines.pop()
    header = [h.strip() for h in lines[0].split(",")]
    nonempty = [l for l in lines[1:] if l.strip().strip(",")]
    maxf = max([len(header)] + [l.count(",") + 1 for l in nonempty])
    n_wide = sum(1 for l in nonempty if l.count(",") + 1 > len(header))
    names = header + [f"_extra{i}" for i in range(maxf - len(header))]
    names = [n if n else f"_blank{i}" for i, n in enumerate(names)]
    seen: dict[str, int] = {}
    dups = []
    for i, n in enumerate(names):
        if n in seen:
            seen[n] += 1
            dups.append(n)
            names[i] = f"{n}.{seen[n]}"
        else:
            seen[n] = 0
    body = "\n".join(lines[1:])
    df = pd.read_csv(io.StringIO(body), header=None, names=names, dtype=str, engine="python",
                     skip_blank_lines=True, keep_default_na=False, na_values=[""])
    df["_source_row"] = np.arange(2, len(df) + 2)  # línea 1 = cabecera (aprox. si hay líneas vacías)
    df = df.dropna(how="all", subset=[c for c in df.columns if c != "_source_row"])
    df = df.rename(columns={k: v for k, v in ALIASES.items() if k in df.columns and v not in df.columns})
    return df, n_wide, sorted(set(dups))


def parse_dates(s: pd.Series) -> pd.Series:
    d4 = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
    d2 = pd.to_datetime(s, format="%d/%m/%y", errors="coerce")
    return d4.fillna(d2)


def to_canonical(raw: pd.DataFrame, div: str, season_code: str) -> tuple[pd.DataFrame, dict]:
    """Convierte un CSV crudo de una división-temporada al esquema canónico."""
    rep: dict = {"non_numeric_values": {}}
    out = pd.DataFrame(index=raw.index)
    for src, dst in SIMPLE_MAP.items():
        out[dst] = raw[src] if src in raw.columns else pd.Series(pd.NA, index=raw.index, dtype="object")
    for dst, (new, old) in REGIME_MAP.items():
        a = raw[new] if new in raw.columns else pd.Series(pd.NA, index=raw.index, dtype="object")
        b = raw[old] if old in raw.columns else pd.Series(pd.NA, index=raw.index, dtype="object")
        out[dst] = a.where(a.notna(), b)
        if dst == "ou_pre_avg_over":
            out["ou_pre_avg_source"] = np.where(a.notna(), "oddsportal", np.where(b.notna(), "betbrain", None))
    # numéricos con registro de valores no numéricos (formato)
    num_cols = [c for c in out.columns if c.startswith(NUMERIC_PREFIXES) and c != "ou_pre_avg_source"] + NUMERIC_STATS
    for c in num_cols:
        raw_vals = out[c]
        conv = pd.to_numeric(raw_vals, errors="coerce")
        bad = raw_vals.notna() & conv.isna()
        if bad.any():
            rep["non_numeric_values"][c] = sorted(raw_vals[bad].astype(str).unique().tolist())[:5]
        out[c] = conv.astype("float64")
    for c in ["home_team", "away_team", "referee", "ftr", "htr", "kickoff_time_uk", "div_raw"]:
        out[c] = out[c].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
        out[c] = out[c].where(out[c] != "", pd.NA)
    out["match_date"] = parse_dates(out["date_raw"].astype("string").str.strip())
    out["div"] = div
    out["season_code"] = season_code
    out["season"] = season_label(season_code)
    out["country"] = DIVISIONS[div]["country"]
    out["competition"] = DIVISIONS[div]["competition"]
    out["source_row"] = raw["_source_row"].values
    # match_id con nombres CRUDOS (identifica la fila de la fuente, estable ante cambios de alias)
    out["match_id"] = make_match_id(div, out["match_date"], out["home_team"].astype("object"),
                                    out["away_team"].astype("object"))
    out["home_team_raw"], out["away_team_raw"] = out["home_team"], out["away_team"]
    aliases = {k: v["canonical"] for k, v in team_aliases().get(DIVISIONS[div]["country"], {}).items()}
    if aliases:
        out["home_team"] = out["home_team"].replace(aliases)
        out["away_team"] = out["away_team"].replace(aliases)
    rep["team_alias_rows"] = int((out["home_team"] != out["home_team_raw"]).fillna(False).sum()
                                 + (out["away_team"] != out["away_team_raw"]).fillna(False).sum())
    # banderas de incoherencia (no se modifican valores crudos)
    exp_htr = np.where(out.hthg > out.htag, "H", np.where(out.hthg < out.htag, "A", "D"))
    out["flag_htr_inconsistent"] = (out["htr"].notna() & out.hthg.notna() & out.htag.notna()
                                    & (out["htr"].astype(str) != exp_htr)).fillna(False).astype(bool)
    out["flag_shots_target_gt_shots"] = ((out.hst > out.hs) | (out.ast > out.as_)).fillna(False).astype(bool)
    out["flag_red_cards_gt_5"] = ((out.hr > 5) | (out.ar > 5)).fillna(False).astype(bool)
    out["total_goals"] = out["fthg"] + out["ftag"]
    out["over25"] = np.where(out["total_goals"].notna(), (out["total_goals"] > 2.5).astype(float), np.nan)
    rep["div_raw_mismatch"] = int((out["div_raw"].notna() & (out["div_raw"] != div)).sum())
    return out, rep


BOOK_CODES_1X2 = ["1XB", "B365", "BF", "BFD", "BFE", "BMGM", "BV", "BS", "BW", "CL", "GB", "IW", "LB", "PP",
                  "PS", "SK", "SO", "SB", "SJ", "SY", "VC", "WH", "BbAv", "BbMx", "Avg", "Max"]
BOOK_CODES_OU = ["B365", "P", "GB", "BbAv", "BbMx", "Avg", "Max"]


def bookmakers_in_header(cols) -> dict[str, list[str]]:
    """Casas/agregados con columnas en la cabecera (metadato; no implica datos no vacíos)."""
    cols = set(cols)
    return {"x12_pre": [c for c in BOOK_CODES_1X2 if f"{c}H" in cols],
            "x12_close": [c for c in BOOK_CODES_1X2 if f"{c}CH" in cols],
            "ou_pre": [c for c in BOOK_CODES_OU if f"{c}>2.5" in cols],
            "ou_close": [c for c in BOOK_CODES_OU if f"{c}C>2.5" in cols]}


def parse_season_zip(zip_path: Path, season_code: str) -> tuple[pd.DataFrame, list[dict]]:
    """Parsea todos los CSV de un data.zip. Devuelve (partidos canónicos, informes por archivo)."""
    frames, reports = [], []
    zsha = sha256_file(zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        for name in sorted(zf.namelist()):
            if not name.endswith(".csv"):
                continue
            div = name[:-4]
            if div not in DIVISIONS:
                reports.append({"season_code": season_code, "file": name, "status": "division_not_in_universe"})
                continue
            text, enc = decode_bytes(zf.read(name))
            raw, n_wide, dups = _read_csv_tolerant(text)
            canon, rep = to_canonical(raw, div, season_code)
            canon["source_file"] = f"{season_code}/{name}"
            canon["raw_zip_sha256"] = zsha
            canon["encoding"] = enc
            frames.append(canon)
            reports.append({"season_code": season_code, "div": div, "file": name, "encoding": enc,
                            "rows": int(len(canon)), "rows_wider_than_header": int(n_wide),
                            "duplicate_header_names": dups, "extra_unnamed_columns": int(
                                sum(c.startswith("_extra") for c in raw.columns)),
                            "bookmakers_in_header": bookmakers_in_header(raw.columns), **rep})
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return df, reports

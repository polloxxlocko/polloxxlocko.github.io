"""Protección del conjunto de prueba final (holdout) y de la reserva prospectiva.

Particiones (configs/holdout.json):
  dev          temporadas <= 2023/24                  uso libre para desarrollo
  holdout      2024/25 y 2025/26                      conjunto de prueba final, SELLADO
  prospective  2026/27 en adelante                    reserva prospectiva (GATE 5), SELLADA

Niveles de acceso a datos reservados:
  Nivel 0  metadatos: id, división, temporada, fecha, hora, equipos, banderas booleanas de
           PRESENCIA/VALIDEZ de campos. Permitido sin autorización (inventario, integridad).
  Nivel 1  valores de cuotas.                           PROHIBIDO sin autorización
  Nivel 2  resultados y estadísticas del partido.       PROHIBIDO sin autorización

Controles:
  1. Separación física: RAW y procesados reservados viven en data/holdout/ y
     data/prospective/, nunca en data/raw/ ni data/processed/dev/.
  2. Registro de match_ids reservados (sin resultados) -> `assert_no_reserved` detecta
     filas reservadas que entren por cualquier vía (p. ej., re-lectura de RAW).
  3. `open_reserved` exige un archivo de autorización del usuario ligado al hash del
     protocolo congelado (PROTOCOL_FREEZE.json); cada apertura se anota en un registro
     append-only (ACCESS_LOG.jsonl).
  4. Test 'tripwire': ningún módulo fuera de paths.py/holdout.py puede nombrar las rutas
     reservadas.
  5. Verificación de hashes de integridad de RAW y procesados reservados.

Regla de procedimiento (CLAUDE.md): ningún agente crea el archivo de autorización por
iniciativa propia; solo tras autorización expresa del usuario en la conversación.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import ingest, paths, temporal

LEVEL0_ID_COLUMNS = [
    "match_id", "div", "season_code", "season", "country", "competition", "match_date",
    "kickoff_time_uk", "home_team", "away_team", "weekday", "kickoff_precision",
    "pre_odds_capture_date_est", "pre_odds_capture_rule", "capture_rule_ambiguous",
    "capture_time_unverifiable", "source_file", "encoding",
]
OU_PAIRS = ["ou_pre_b365", "ou_pre_pin", "ou_pre_gb", "ou_pre_avg", "ou_pre_max",
            "ou_close_b365", "ou_close_pin", "ou_close_avg", "ou_close_max"]
X12_TRIPLES = ["x12_pre_b365", "x12_pre_pin", "x12_pre_avg", "x12_close_b365", "x12_close_pin", "x12_close_avg"]
STAT_PRESENCE = {"result": ["fthg", "ftag"], "halftime": ["hthg", "htag"], "shots": ["hs", "as_"],
                 "shots_target": ["hst", "ast"], "corners": ["hc", "ac"], "fouls": ["hf", "af"],
                 "yellow": ["hy", "ay"], "red": ["hr", "ar"], "referee": ["referee"], "xg": ["hxg", "axg"],
                 "attendance": ["attendance"]}


class ReservedDataError(RuntimeError):
    """Se intentó usar datos reservados (holdout/prospectivo) fuera del protocolo."""


# ---------------------------------------------------------------- rutas internas
def _part_dir(partition: str) -> Path:
    if partition == "holdout":
        return paths.HOLDOUT_DIR
    if partition == "prospective":
        return paths.PROSPECTIVE_DIR
    raise ValueError(partition)


def _registry_path(partition: str) -> Path:
    return _part_dir(partition) / "registry.json"


def _access_log(partition: str) -> Path:
    return _part_dir(partition) / "ACCESS_LOG.jsonl"


def _full_path(partition: str) -> Path:
    return _part_dir(partition) / "processed" / "matches_full.parquet"


def _level0_path(partition: str) -> Path:
    return _part_dir(partition) / "processed" / "metadata_level0.parquet"


def _raw_zips(partition: str) -> list[tuple[str, Path]]:
    root = _part_dir(partition) / "raw" / "football_data"
    out = []
    for z in sorted(root.glob("*/data.zip")):
        code = z.parent.name
        if paths.partition_of(code) != partition:
            raise ReservedDataError(f"{z} no pertenece a la partición {partition}")
        out.append((code, z))
    return out


def reserved_retrieved_at() -> dict[str, str]:
    """Fecha UTC de descarga de temporadas reservadas (desde sus manifiestos; sin contenido)."""
    out: dict[str, str] = {}
    for part in ("holdout", "prospective"):
        mf = _part_dir(part) / "raw" / "football_data" / "manifest.jsonl"
        if mf.exists():
            for line in mf.read_text().splitlines():
                r = json.loads(line)
                if r.get("status") == "downloaded":
                    out[r["season_code"]] = r["retrieved_at_utc"]
    return out


# ---------------------------------------------------------------- hashes
PROVENANCE_TIME_COLUMNS = ("dataset_retrieved_at_utc",)


def content_hash(df: pd.DataFrame) -> str:
    """Hash determinista del CONTENIDO (independiente del formato Parquet y de la fecha de
    descarga: las columnas de procedencia temporal se excluyen y se registran aparte)."""
    d = df.drop(columns=[c for c in PROVENANCE_TIME_COLUMNS if c in df.columns])
    d = d.sort_values("match_id").reset_index(drop=True)
    d = d[sorted(d.columns)]
    csv = d.to_csv(index=False, float_format="%.6g", date_format="%Y-%m-%dT%H:%M:%S%z")
    return hashlib.sha256(csv.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- nivel 0
def _pair_valid(df: pd.DataFrame, prefix: str) -> pd.Series:
    o, u = df.get(f"{prefix}_over"), df.get(f"{prefix}_under")
    if o is None or u is None:
        return pd.Series(False, index=df.index)
    return (o >= 1.01) & (u >= 1.01)


def _pair_overround_in_range(df: pd.DataFrame, prefix: str, lo=0.0, hi=0.25) -> pd.Series:
    v = _pair_valid(df, prefix)
    ov = 1 / df[f"{prefix}_over"] + 1 / df[f"{prefix}_under"] - 1
    return v & ov.between(lo, hi)


def level0_metadata(full: pd.DataFrame) -> pd.DataFrame:
    """Metadatos de nivel 0: identidad + banderas booleanas. Sin valores de cuotas ni resultados."""
    m = full[LEVEL0_ID_COLUMNS].copy()
    for p in OU_PAIRS:
        m[f"has_{p}_pair"] = _pair_valid(full, p).values
    m["ou_pre_avg_overround_in_range"] = _pair_overround_in_range(full, "ou_pre_avg").values
    m["ou_close_avg_overround_in_range"] = _pair_overround_in_range(full, "ou_close_avg").values
    m["ou_pre_avg_source"] = full["ou_pre_avg_source"].values
    for t in X12_TRIPLES:
        m[f"has_{t}"] = ((full[f"{t}_h"] >= 1.01) & (full[f"{t}_d"] >= 1.01) & (full[f"{t}_a"] >= 1.01)).values
    for name, cols in STAT_PRESENCE.items():
        m[f"has_{name}"] = np.logical_and.reduce([full[c].notna().values for c in cols])
    m["rows_wider_flag"] = False
    return m


# ---------------------------------------------------------------- sellado
def seal(partition: str, retrieved_at_utc: dict[str, str] | None = None) -> dict:
    """Procesa RAW reservado -> parquet completo (sellado) + metadatos nivel 0 + registro.
    Devuelve SOLO un resumen de nivel 0."""
    zips = _raw_zips(partition)
    frames, file_reports = [], []
    for code, z in zips:
        df, reps = ingest.parse_season_zip(z, code)
        frames.append(df)
        file_reports += reps
    full = pd.concat(frames, ignore_index=True)
    full = temporal.add_temporal_fields(full, retrieved_at_utc)
    full["partition"] = partition
    # match_id = sha1(div|fecha|local|visitante): duplicado de match_id <=> clave duplicada
    full["duplicate_key"] = full["match_id"].duplicated(keep=False)
    lvl0 = level0_metadata(full)
    lvl0["duplicate_key"] = full["duplicate_key"].values
    pdir = _part_dir(partition) / "processed"
    pdir.mkdir(parents=True, exist_ok=True)
    full.to_parquet(_full_path(partition), index=False)
    lvl0.to_parquet(_level0_path(partition), index=False)
    reg = {
        "partition": partition,
        "sealed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "seasons": sorted(full["season_code"].unique().tolist()),
        "n_matches": int(len(full)),
        "match_ids": sorted(full["match_id"].unique().tolist()),
        "raw_files": {code: {"path": str(z.relative_to(paths.ROOT)), "sha256": ingest.sha256_file(z)} for code, z in zips},
        "full_content_sha256": content_hash(full),
        "level0_content_sha256": content_hash(lvl0),
        "file_reports_level0": [{k: v for k, v in r.items() if k not in ("non_numeric_values",)} for r in file_reports],
    }
    _registry_path(partition).write_text(json.dumps(reg, indent=1, ensure_ascii=False, default=str))
    return {k: v for k, v in reg.items() if k != "match_ids"}


# ---------------------------------------------------------------- guardas
def registry(partition: str) -> dict:
    p = _registry_path(partition)
    if not p.exists():
        raise ReservedDataError(f"Registro de {partition} inexistente: ejecute el sellado (qsports build).")
    return json.loads(p.read_text())


def reserved_ids() -> set[str]:
    ids: set[str] = set()
    for part in ("holdout", "prospective"):
        try:
            ids |= set(registry(part)["match_ids"])
        except ReservedDataError:
            pass
    return ids


def assert_no_reserved(df: pd.DataFrame, context: str = "") -> None:
    """Falla si el DataFrame contiene temporadas reservadas o match_ids registrados como reservados.
    Debe llamarse en todo pipeline de features/modelos antes de usar los datos."""
    if "season_code" in df.columns:
        parts = {paths.partition_of(s) for s in df["season_code"].dropna().unique()}
        if parts - {"dev"}:
            raise ReservedDataError(f"[{context}] temporadas reservadas presentes: {sorted(parts - {'dev'})}")
    if "match_id" in df.columns:
        leaked = set(df["match_id"].dropna().unique()) & reserved_ids()
        if leaked:
            raise ReservedDataError(f"[{context}] {len(leaked)} match_id reservados presentes")


def load_level0(partition: str) -> pd.DataFrame:
    """Metadatos de nivel 0 (permitidos sin autorización)."""
    return pd.read_parquet(_level0_path(partition))


def protocol_freeze_hash() -> str | None:
    """Hash del protocolo congelado: SHA-256 de los archivos listados en PROTOCOL_FREEZE.json."""
    cfg = paths.holdout_config()
    p = paths.ROOT / cfg["protocol_freeze_file"]
    if not p.exists():
        return None
    files = json.loads(p.read_text())["files"]
    h = hashlib.sha256()
    for f in sorted(files):
        h.update(f.encode())
        h.update(ingest.sha256_file(paths.ROOT / f).encode())
    return h.hexdigest()


def _check_authorization(partition: str) -> dict:
    cfg = paths.holdout_config()
    fname = cfg["authorization_file"] if partition == "holdout" else cfg["prospective_authorization_file"]
    p = paths.ROOT / fname
    if not p.exists():
        raise ReservedDataError(
            f"Partición '{partition}' SELLADA. No existe {fname}. Solo puede abrirse con autorización expresa "
            f"del usuario, después de congelar el protocolo (ver HOLDOUT_PROTECTION_PROTOCOL.md).")
    auth = json.loads(p.read_text())
    if auth.get("partition") != partition:
        raise ReservedDataError("La autorización no corresponde a esta partición.")
    freeze = protocol_freeze_hash()
    if freeze is None:
        raise ReservedDataError("No existe PROTOCOL_FREEZE.json: el protocolo no está congelado.")
    if auth.get("protocol_freeze_sha256") != freeze:
        raise ReservedDataError("El protocolo cambió después de la autorización (hash distinto). Acceso denegado.")
    for k in ("authorized_by", "authorized_at", "user_statement", "purpose"):
        if not auth.get(k):
            raise ReservedDataError(f"Autorización incompleta: falta '{k}'.")
    return auth


def open_reserved(partition: str, purpose: str) -> pd.DataFrame:
    """Abre datos reservados completos (niveles 1-2). Requiere autorización válida. Registra el acceso."""
    auth = _check_authorization(partition)
    df = pd.read_parquet(_full_path(partition))
    with _access_log(partition).open("a") as f:
        f.write(json.dumps({"at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "partition": partition,
                            "purpose": purpose, "authorized_by": auth["authorized_by"],
                            "protocol_freeze_sha256": auth["protocol_freeze_sha256"]}, ensure_ascii=False) + "\n")
    return df


def verify_integrity(partition: str) -> dict:
    """Comprueba que RAW y procesados reservados no cambiaron desde el sellado (sin leer contenidos
    más allá del hash)."""
    reg = registry(partition)
    res = {"partition": partition, "raw_ok": True, "level0_ok": None, "details": {}}
    for code, info in reg["raw_files"].items():
        cur = ingest.sha256_file(paths.ROOT / info["path"])
        ok = cur == info["sha256"]
        res["details"][code] = ok
        res["raw_ok"] &= ok
    lvl0 = load_level0(partition)
    res["level0_ok"] = content_hash(lvl0) == reg["level0_content_sha256"]
    return res

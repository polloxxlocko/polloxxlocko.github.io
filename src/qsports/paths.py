"""Rutas del proyecto. ÚNICO lugar (junto con holdout.py) donde se nombran los
directorios reservados. El test `test_tripwire_reserved_paths` falla si otro módulo los
referencia directamente."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIGS = ROOT / "configs"
DATA = ROOT / "data"

# Desarrollo (de libre uso)
RAW_DEV = DATA / "raw" / "football_data"
PROCESSED_DEV = DATA / "processed" / "dev"
FEATURES_DEV = DATA / "features" / "dev"
DATA_MANIFEST = DATA / "processed" / "MANIFEST.json"

# Reservados (acceso solo vía qsports.holdout)
HOLDOUT_DIR = DATA / "holdout"
RESERVE_DIR = DATA / "reserve"

REPORTS_GATE1 = ROOT / "reports" / "gate1"


def holdout_config() -> dict:
    return json.loads((CONFIGS / "holdout.json").read_text())


def partition_of(season_code: str) -> str:
    """'dev' | 'holdout' | 'reserve' para un código de temporada 'YYyy'."""
    cfg = holdout_config()
    if season_code in cfg["holdout_seasons"]:
        return "holdout"
    if season_code >= cfg["reserve_from_season"]:
        return "reserve"
    if season_code > cfg["dev_last_season"]:
        # Hueco no previsto entre dev y holdout: se trata como reservado por seguridad.
        return "holdout"
    return "dev"


def raw_dir_for(season_code: str) -> Path:
    part = partition_of(season_code)
    if part == "dev":
        return RAW_DEV
    return (HOLDOUT_DIR if part == "holdout" else RESERVE_DIR) / "raw" / "football_data"

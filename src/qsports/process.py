"""Pipeline de construcción GATE 1: RAW -> PROCESSED (dev) + sellado de reservados + FEATURES
de benchmark (dev) + manifiesto de integridad.

Orden (importante): 1) sellar holdout y prospectivo (crea los registros de match_ids),
2) construir dev y verificar con `assert_no_reserved`, 3) benchmarks dev, 4) manifiesto.
"""
from __future__ import annotations

import datetime as dt
import json
import platform
import subprocess
from importlib import metadata

import numpy as np
import pandas as pd

from . import benchmark, holdout, ingest, paths, temporal


def retrieved_at_map() -> dict[str, str]:
    """Fecha UTC de descarga por temporada, desde los manifiestos RAW (append-only)."""
    out: dict[str, str] = {}
    mf = paths.RAW_DEV / "manifest.jsonl"
    if mf.exists():
        for line in mf.read_text().splitlines():
            r = json.loads(line)
            if r.get("status") == "downloaded" and paths.partition_of(r["season_code"]) == "dev":
                out[r["season_code"]] = r["retrieved_at_utc"]
    out |= holdout.reserved_retrieved_at()  # metadatos de descarga (sin contenido) de reservados
    return out


def season_window_ok(df: pd.DataFrame) -> pd.Series:
    """Fecha dentro de [1-jun año inicio, 31-ago año fin] (tolerancia para la temporada COVID 2019/20)."""
    y0 = 2000 + df["season_code"].str[:2].astype(int)
    start = pd.to_datetime(y0.astype(str) + "-06-01")
    end = pd.to_datetime((y0 + 1).astype(str) + "-08-31")
    return df["match_date"].between(start, end)


def build_dev(retrieved: dict[str, str]) -> tuple[pd.DataFrame, list[dict]]:
    frames, reports = [], []
    for code, z in ingest.iter_dev_zips():
        df, reps = ingest.parse_season_zip(z, code)
        frames.append(df)
        reports += reps
    dev = pd.concat(frames, ignore_index=True)
    dev = temporal.add_temporal_fields(dev, retrieved)
    dev["partition"] = "dev"
    # match_id = sha1(div|fecha|local|visitante): duplicado de match_id <=> clave duplicada
    dev["duplicate_key"] = dev["match_id"].duplicated(keep=False)
    dev["date_in_season_window"] = season_window_ok(dev)
    holdout.assert_no_reserved(dev, "build_dev")
    return dev, reports


def git_head() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=paths.ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return None


def build(download: bool = False, first: str = "0001", last: str = "2627") -> dict:
    if download:
        ingest.download_seasons(ingest.season_codes(first, last))
    retrieved = retrieved_at_map()
    summary: dict = {"built_at_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
    for part in ("holdout", "reserve"):
        if holdout.has_raw(part):
            summary[f"sealed_{part}"] = holdout.seal(part, retrieved)
        else:  # auditoría sin temporadas reservadas: se conserva el registro versionado (ids, hashes)
            summary[f"sealed_{part}"] = {k: v for k, v in holdout.registry(part).items() if k != "match_ids"}
            summary[f"sealed_{part}"]["note"] = "RAW reservado ausente: sellado omitido; registro versionado conservado"
    dev, reports = build_dev(retrieved)
    paths.PROCESSED_DEV.mkdir(parents=True, exist_ok=True)
    dev.to_parquet(paths.PROCESSED_DEV / "matches.parquet", index=False)
    (paths.PROCESSED_DEV / "file_reports.json").write_text(json.dumps(reports, indent=1, ensure_ascii=False))
    lvl0_dev = holdout.level0_metadata(dev)
    lvl0_dev["duplicate_key"] = dev["duplicate_key"].values
    lvl0_dev.to_parquet(paths.PROCESSED_DEV / "metadata_level0.parquet", index=False)

    bench = benchmark.market_benchmarks(dev)
    bench["p_C_hist_freq"] = benchmark.historical_frequency(dev)
    bench["season_code"] = dev["season_code"].values
    bench["div"] = dev["div"].values
    holdout.assert_no_reserved(bench, "benchmarks_dev")
    paths.FEATURES_DEV.mkdir(parents=True, exist_ok=True)
    bench.to_parquet(paths.FEATURES_DEV / "market_benchmarks.parquet", index=False)

    raw_dev = {code: {"path": str(z.relative_to(paths.ROOT)), "sha256": ingest.sha256_file(z)}
               for code, z in ingest.iter_dev_zips()}
    manifest = {
        "dataset_version": f"fd-{dt.date.today().isoformat()}-{holdout.content_hash(dev)[:12]}",
        "created_at_utc": summary["built_at_utc"],
        "code_git_head": git_head(),
        "python": platform.python_version(),
        "packages": {p: metadata.version(p) for p in ("numpy", "pandas", "pyarrow", "requests")},
        "raw_dev_files": raw_dev,
        "outputs": {
            "processed/dev/matches.parquet": {"rows": int(len(dev)), "content_sha256": holdout.content_hash(dev),
                                              "seasons": sorted(dev["season_code"].unique().tolist())},
            "processed/dev/metadata_level0.parquet": {"rows": int(len(lvl0_dev)),
                                                      "content_sha256": holdout.content_hash(lvl0_dev)},
            "features/dev/market_benchmarks.parquet": {"rows": int(len(bench)),
                                                       "content_sha256": holdout.content_hash(bench)},
        },
        "reserved": {part: {k: v for k, v in summary[f"sealed_{part}"].items() if k != "file_reports_level0"}
                     for part in ("holdout", "reserve")},
    }
    paths.DATA_MANIFEST.write_text(json.dumps(manifest, indent=1, ensure_ascii=False, default=str))
    summary["dev_rows"] = int(len(dev))
    summary["manifest"] = str(paths.DATA_MANIFEST.relative_to(paths.ROOT))
    return summary


def load_dev() -> pd.DataFrame:
    """Único punto de carga del dataset de desarrollo. Verifica que no haya datos reservados."""
    df = pd.read_parquet(paths.PROCESSED_DEV / "matches.parquet")
    holdout.assert_no_reserved(df, "load_dev")
    return df


def load_dev_benchmarks() -> pd.DataFrame:
    df = pd.read_parquet(paths.FEATURES_DEV / "market_benchmarks.parquet")
    holdout.assert_no_reserved(df, "load_dev_benchmarks")
    return df

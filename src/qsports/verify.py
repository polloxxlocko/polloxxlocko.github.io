"""Verificación de integridad y de invariantes de protección (python -m qsports verify)."""
from __future__ import annotations

import json

from . import holdout, ingest, paths, process


def verify_all() -> dict:
    res: dict = {"checks": {}}
    c = res["checks"]
    man = json.loads(paths.DATA_MANIFEST.read_text())
    # 1. RAW dev sin cambios
    c["raw_dev_hashes_match_manifest"] = all(
        ingest.sha256_file(paths.ROOT / v["path"]) == v["sha256"] for v in man["raw_dev_files"].values())
    # 2. RAW dev coincide con la descarga original de Fase Cero (manifest.jsonl)
    orig = {}
    for line in (paths.RAW_DEV / "manifest.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r.get("status") == "downloaded":
            orig[r["season_code"]] = r["sha256"]
    c["raw_dev_hashes_match_original_download"] = all(
        orig.get(k) == v["sha256"] for k, v in man["raw_dev_files"].items())
    # 3. Ninguna temporada reservada en RAW de desarrollo
    c["no_reserved_seasons_in_raw_dev"] = all(paths.partition_of(p.name) == "dev"
                                              for p in paths.RAW_DEV.iterdir() if p.is_dir())
    # 4. Dev procesado: sin reservados y con el hash del manifiesto
    try:
        dev = process.load_dev()
        bench = process.load_dev_benchmarks()
        c["dev_contains_no_reserved"] = True
        c["dev_content_hash_matches_manifest"] = (holdout.content_hash(dev) ==
                                                  man["outputs"]["processed/dev/matches.parquet"]["content_sha256"])
        c["benchmarks_content_hash_matches_manifest"] = (holdout.content_hash(bench) ==
                                                         man["outputs"]["features/dev/market_benchmarks.parquet"]["content_sha256"])
    except holdout.ReservedDataError as e:
        c["dev_contains_no_reserved"] = False
        res["error"] = str(e)
    # 5. Reservados intactos
    for part in ("holdout", "reserve"):
        v = holdout.verify_integrity(part)
        c[f"{part}_raw_unchanged"] = v["raw_ok"]
        c[f"{part}_level0_unchanged"] = v["level0_ok"]
    # 6. Estado del sello (informativo: debe seguir sellado en GATE 1)
    cfg = paths.holdout_config()
    res["holdout_sealed"] = not (paths.ROOT / cfg["authorization_file"]).exists()
    res["reserve_sealed"] = not (paths.ROOT / cfg["reserve_authorization_file"]).exists()
    res["access_log_entries"] = {p: (len((holdout._access_log(p)).read_text().splitlines())
                                     if holdout._access_log(p).exists() else 0) for p in ("holdout", "reserve")}
    res["ok"] = all(c.values()) and res["holdout_sealed"] and res["reserve_sealed"]
    return res

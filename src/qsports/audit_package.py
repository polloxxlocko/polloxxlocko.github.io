"""Construye el paquete de auditoría reproducible de GATE 2 (exigencia 8).

Contenido: `git archive` del commit actual (código, pruebas, configs, documentación, predicciones
fuera de muestra y registros de experimentos) + AUDIT_RUN.md. Excluye por construcción los datos de
la fuente y todo dato sellado (no están versionados). Verifica el contenido antes de terminar.
"""
from __future__ import annotations

import subprocess
import tarfile

from . import paths
from .holdout import RESERVED_PATH_MARKERS

FORBIDDEN_SUFFIXES = (".zip", ".env")
FORBIDDEN_PARTS = RESERVED_PATH_MARKERS + ("metadata_level0.parquet", "abstracts_local.json",
                                           "data/processed/dev/matches.parquet")
ALLOWED_BASENAMES = ("manifest.jsonl",)  # manifiestos de hashes y URL (nivel 0, versionados)


def is_forbidden(name: str) -> bool:
    """True si un archivo del paquete es un dato de la fuente, sellado o con licencia restrictiva."""
    if name.endswith(FORBIDDEN_SUFFIXES):
        return True
    return any(p in name for p in FORBIDDEN_PARTS) and not name.endswith(ALLOWED_BASENAMES)


def build(out_name: str = "audit_package_gate2.tar.gz") -> str:
    dist = paths.ROOT / "dist"
    dist.mkdir(exist_ok=True)
    out = dist / out_name
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=paths.ROOT, capture_output=True, text=True,
                          check=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=paths.ROOT, capture_output=True, text=True).stdout
    if dirty.strip():
        raise SystemExit("Hay cambios sin commit: el paquete debe corresponder a un commit exacto.")
    subprocess.run(["git", "archive", "--format=tar.gz", f"--prefix=quantitative-sports-{head}/", "-o", str(out), "HEAD"],
                   cwd=paths.ROOT, check=True)
    with tarfile.open(out) as tf:
        files = [m.name for m in tf.getmembers() if m.isfile()]
    bad = [n for n in files if is_forbidden(n)]
    if bad:
        out.unlink()
        raise SystemExit(f"Contenido prohibido en el paquete: {bad[:5]}")
    print(f"{out} ({out.stat().st_size / 1e6:.1f} MB, commit {head}, {len(files)} archivos; sin datos de la fuente ni sellados)")
    return str(out)

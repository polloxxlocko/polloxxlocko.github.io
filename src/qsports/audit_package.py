"""Construye el paquete de auditoría reproducible de GATE 2 (exigencia 8).

Contenido: `git archive` del commit actual (código, pruebas, configs, documentación, predicciones
fuera de muestra y registros de experimentos) + AUDIT_RUN.md. Excluye por construcción los datos de
la fuente y todo dato sellado (no están versionados). Verifica el contenido antes de terminar.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import tarfile
import zipfile

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


# ---------------------------------------------------------------- ZIP ligero (GATE 2.1)
LIGHT_TOP_FILES = ("pyproject.toml", "requirements-lock.txt", ".gitignore")
LIGHT_DIRS = ("src/", "tests/", "configs/", "logs/", "data/synthetic/", "experiments/", "reports/gate2_1/", "phase0/")
LIGHT_LEVEL0 = ("registry.json", "ACCESS_LOG.jsonl", "manifest.jsonl", "MANIFEST.json")


def light_selected(name: str) -> bool:
    """Código fuente, pruebas, configuración, documentación, dependencias, datos sintéticos y los metadatos de
    nivel 0 que el código necesita para fallar cerrado. Sin Parquet ni datos de la fuente o sellados."""
    if is_forbidden(name) or name.endswith(".parquet"):
        return False
    if name.endswith(".md") and "/" not in name:
        return True
    if name in LIGHT_TOP_FILES:
        return True
    if name.startswith("data/"):
        return name.startswith("data/synthetic/") or name.endswith(LIGHT_LEVEL0)
    if name.startswith("experiments/"):
        return name.endswith((".py", ".json", ".csv", ".md", ".txt")) and "/aborted_" not in name
    return name.startswith(LIGHT_DIRS)


def build_light(out_name: str = "audit_package_gate2_1_light.zip") -> str:
    dist = paths.ROOT / "dist"
    dist.mkdir(exist_ok=True)
    out = dist / out_name
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=paths.ROOT, capture_output=True, text=True,
                          check=True).stdout.strip()
    if subprocess.run(["git", "status", "--porcelain"], cwd=paths.ROOT, capture_output=True, text=True).stdout.strip():
        raise SystemExit("Hay cambios sin commit: el paquete debe corresponder a un commit exacto.")
    names = subprocess.run(["git", "ls-tree", "-r", "--name-only", "HEAD"], cwd=paths.ROOT, capture_output=True,
                           text=True, check=True).stdout.splitlines()
    sel = sorted(n for n in names if light_selected(n))
    prefix = f"quantitative-sports-{head}-light/"
    manifest = {}
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for n in sel:
            data = subprocess.run(["git", "show", f"HEAD:{n}"], cwd=paths.ROOT, capture_output=True, check=True).stdout
            manifest[n] = hashlib.sha256(data).hexdigest()
            z.writestr(prefix + n, data)
        z.writestr(prefix + "PACKAGE_MANIFEST.json", json.dumps(
            {"commit": head, "files": len(sel), "sha256": manifest,
             "excluded": "Parquet (predicciones históricas, variables), CSV/ZIP de la fuente, datos sellados, "
                         "resúmenes de artículos, credenciales"}, indent=1))
    with zipfile.ZipFile(out) as z:
        bad = [i.filename for i in z.infolist() if not i.is_dir() and (is_forbidden(i.filename)
                                                                     or i.filename.endswith(".parquet"))]
    if bad:
        out.unlink()
        raise SystemExit(f"Contenido prohibido en el ZIP ligero: {bad[:5]}")
    print(f"{out} ({out.stat().st_size / 1e6:.2f} MB, commit {head}, {len(sel)} archivos + PACKAGE_MANIFEST.json; "
          f"sin Parquet ni datos de la fuente o sellados)")
    return str(out)

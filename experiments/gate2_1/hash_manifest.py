"""Manifiesto de hashes de GATE 2.1 (exigencia 9): código, configuración, dataset, artefactos publicados de
GATE 2, ejecución reproducida, salidas de GATE 2.1, documentación y metadatos sellados de nivel 0.

Uso: python experiments/gate2_1/hash_manifest.py --repro experiments/gate2_1/repro_run
Salida: reports/gate2_1/HASH_MANIFEST.json
"""
import argparse
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path

from qsports import gate2, paths

ROOT = paths.ROOT


def sha(p: Path) -> str:
    return gate2.sha256_file(p)


def tree(d: Path, pattern="*") -> dict:
    return {str(f.relative_to(ROOT)): sha(f) for f in sorted(d.rglob(pattern)) if f.is_file() and "__pycache__" not in f.parts}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repro", required=True)
    a = ap.parse_args()
    rep = Path(a.repro)
    man = json.loads((rep / "RUN_MANIFEST.json").read_text())
    git = lambda *x: subprocess.run(["git", *x], cwd=ROOT, capture_output=True, text=True).stdout.strip()  # noqa: E731
    out = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "git_head_at_generation": git("rev-parse", "HEAD"),
        "note": "SHA-256 de cada archivo. Los Parquet de la reproducción no se versionan; sus hashes están aquí y en "
                "RUN_MANIFEST.json, y se regeneran con run.py --clean.",
        "code": {"files_sha256": gate2.code_files(), "code_hash": gate2.code_hash(),
                 "experiment_scripts": {**tree(ROOT / "experiments" / "gate2", "*.py"),
                                        **tree(ROOT / "experiments" / "gate2_1", "*.py")}},
        "dataset": {**gate2.dataset_hashes(),
                    "raw_dev_manifest_sha256": sha(paths.RAW_DEV / "manifest.jsonl"),
                    "processed_manifest_sha256": sha(paths.DATA_MANIFEST)},
        "sealed_level0": {str(f.relative_to(ROOT)): sha(f) for f in sorted((ROOT / "data").glob("*/registry.json"))}
        | {str(f.relative_to(ROOT)): sha(f) for f in sorted((ROOT / "data").glob("*/ACCESS_LOG.jsonl"))}
        | {str(paths.FENCE_LOG.relative_to(ROOT)): sha(paths.FENCE_LOG)},
        "published_gate2_artifacts": tree(ROOT / "experiments" / "gate2"),
        "reproduction_run": {"dir": str(rep.relative_to(ROOT)) if rep.is_relative_to(ROOT) else str(rep),
                             "git_commit": man["git_commit"], "code_hash": man["code_hash"], "clean": man["clean"],
                             "artifacts_set_sha256": man.get("artifacts_set_sha256"),
                             "n_artifacts": len(man.get("artifacts_sha256", {})),
                             "run_manifest_sha256": sha(rep / "RUN_MANIFEST.json"),
                             "all_files_sha256": {str(f.relative_to(rep)): sha(f) for f in sorted(rep.rglob("*"))
                                                  if f.is_file()}},
        "gate2_1_outputs": {k: v for k, v in tree(ROOT / "experiments" / "gate2_1").items()
                            if not k.endswith(".parquet") and "/repro_run/" not in k},
        "synthetic_data": tree(ROOT / "data" / "synthetic"),
        "documents": {f.name: sha(f) for f in sorted(ROOT.glob("*.md"))},
    }
    out["manifest_sha256_of_contents"] = hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest()
    dst = ROOT / "reports" / "gate2_1" / "HASH_MANIFEST.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(dst, len(out["published_gate2_artifacts"]), "artefactos publicados;", out["reproduction_run"]["n_artifacts"],
          "artefactos reproducidos")


if __name__ == "__main__":
    main()

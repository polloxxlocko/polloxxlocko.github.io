"""Manifiesto de hashes de GATE 3 -> experiments/gate3/records/HASH_MANIFEST_GATE3.json"""
import datetime as dt
import hashlib
import json
import subprocess

from qsports import gate2, gate3, paths

ROOT = paths.ROOT


def tree(d, skip=()):
    return {str(f.relative_to(ROOT)): gate2.sha256_file(f) for f in sorted(d.rglob("*"))
            if f.is_file() and "__pycache__" not in f.parts and not any(s in str(f) for s in skip)}


def main():
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    out = {"generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "git_head_at_generation": head,
           "code": {"files_sha256": gate2.code_files(), "code_hash": gate2.code_hash(),
                    "frozen_code_hash": gate3.load_frozen()["code_hash"]},
           "frozen_candidates": {gate3.FROZEN_REL: gate2.sha256_file(gate3.frozen_path())},
           "authorization": {"GATE3_AUTHORIZATION.json": gate2.sha256_file(ROOT / "GATE3_AUTHORIZATION.json")},
           "seal": {"logs/GATE3_EVALUATED.json": gate2.sha256_file(gate3.seal_path())},
           "fence_log": {"logs/GATE3_FENCE_LOG.jsonl": gate2.sha256_file(paths.FENCE_LOG)},
           "sealed_level0": {str(f.relative_to(ROOT)): gate2.sha256_file(f) for f in sorted((ROOT / "data").glob("*/registry.json"))}
           | {str(f.relative_to(ROOT)): gate2.sha256_file(f) for f in sorted((ROOT / "data").glob("*/ACCESS_LOG.jsonl"))},
           "dataset": gate2.dataset_hashes(),
           "validation_run": tree(ROOT / "experiments" / "gate3" / "validation_run"),
           "reference_reproduction": tree(ROOT / "experiments" / "gate3" / "repro_run"),
           "comparisons": tree(ROOT / "experiments" / "gate3", skip=("validation_run", "repro_run", "records")),
           "documents": {f.name: gate2.sha256_file(f) for f in sorted(ROOT.glob("*.md"))}}
    out["code_hash_matches_frozen"] = out["code"]["code_hash"] == out["code"]["frozen_code_hash"]
    out["manifest_sha256_of_contents"] = hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest()
    dst = ROOT / "experiments" / "gate3" / "records" / "HASH_MANIFEST_GATE3.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(dst, "validación:", len(out["validation_run"]), "archivos; referencia:", len(out["reference_reproduction"]),
          "; hash de código = congelado:", out["code_hash_matches_frozen"])


if __name__ == "__main__":
    main()

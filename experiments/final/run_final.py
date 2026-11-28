"""Ejecutor de la prueba final (holdout 2024/25-2025/26). Preparado en GATE 4; NO autorizado todavía.

Uso:
  python experiments/final/run_final.py freeze --power experiments/gate4/power_gate3.json  # congela la prueba final
  python experiments/final/run_final.py verify          # identidad + hash del dataset de desarrollo (sin holdout)
  python experiments/final/run_final.py run --out DIR   # UNA sola evaluación; exige HOLDOUT_AUTHORIZATION.json
HOLDOUT_AUTHORIZATION.json solo se crea por instrucción expresa del usuario, ligado al hash de PROTOCOL_FREEZE.json.
"""
import argparse
import json
import os
import sys

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

from qsports import final_test, process  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("freeze")
    f.add_argument("--power", default=None)
    sub.add_parser("verify")
    r = sub.add_parser("run")
    r.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "freeze":
        power = json.loads(open(a.power).read()) if a.power else None
        s = final_test.build_spec(power)
        print(json.dumps({k: s[k] for k in ("code_hash", "holdout_seasons", "dataset")}, indent=1, ensure_ascii=False))
    elif a.cmd == "verify":
        spec = final_test.load_spec()
        rep = final_test.verify_spec(spec, require_inputs=True)
        rep["dev_dataset"] = final_test.verify_dev_dataset(spec, process.load_dev(), process.load_dev_benchmarks())
        print(json.dumps(rep, indent=1, ensure_ascii=False))
    else:
        rep = final_test.run_final(a.out)
        print(json.dumps(rep["evaluation"]["verdicts"], indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Ejecutor de GATE 3 (validación 2022/23-2023/24, una sola evaluación de los candidatos congelados).

Uso:
  python experiments/gate3/run_gate3.py freeze --reference DIR   # escribe configs/gate3_frozen_candidates.json
  python experiments/gate3/run_gate3.py verify                    # comprobaciones de identidad (sin evaluar)
  python experiments/gate3/run_gate3.py run --out DIR             # evaluación única (exige autorización)
La autorización (GATE3_AUTHORIZATION.json) solo se crea por instrucción expresa del usuario.
"""
import argparse
import json
import os
import sys

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

from qsports import gate3  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("freeze")
    f.add_argument("--reference", required=True)
    sub.add_parser("verify")
    r = sub.add_parser("run")
    r.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "freeze":
        fr = gate3.freeze(a.reference)
        print(json.dumps({k: fr[k] for k in ("reference_run", "code_hash", "candidates")}, indent=1, ensure_ascii=False))
    elif a.cmd == "verify":
        print(json.dumps(gate3.verify_frozen(gate3.load_frozen()), indent=1, ensure_ascii=False, default=str))
    else:
        rep = gate3.run(a.out)
        ev = rep["evaluation"]
        print(json.dumps({"n": ev["n"], "identity_replay_inner": rep["identity_replay_inner"],
                          **{k: [round(v["delta_logloss"]["mean"], 5), round(v["delta_logloss"]["lo"], 5),
                                 round(v["delta_logloss"]["hi"], 5), v["category"]] for k, v in ev["comparisons"].items()}},
                         indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

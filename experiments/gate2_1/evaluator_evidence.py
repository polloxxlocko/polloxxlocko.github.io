"""Evidencia cuantitativa del evaluador corregido (GATE 2.1, exigencias 2 y 3), solo con datos sintéticos.

1. Cobertura del IC al 95% bajo dependencia serial sintética (shock semanal AR(1) común, con pausas entre
   temporadas) según el bloque (1, 2, 4, 8, 12 semanas) y la definición de semana (calendario o activa).
2. Tamaño del Diebold-Mariano (H0 cierta) con y sin corrección HAC.
3. Cobertura sin dependencia (control).
4. Ejemplo de validación de entradas: qué se rechaza.
Uso: python experiments/gate2_1/evaluator_evidence.py  -> experiments/gate2_1/evaluator_evidence.json
"""
import json
import math
from pathlib import Path

import numpy as np

from qsports import evaluation as ev
from qsports.validation import InputValidationError

OUT = Path(__file__).resolve().parent / "evaluator_evidence.json"


def season_weeks(n_seasons=6, active=38, pause=14):
    return np.concatenate([np.arange(active) + s * (active + pause) for s in range(n_seasons)])


def ar1(n, phi, sd, rng):
    u = np.empty(n)
    u[0] = rng.normal(0, sd / math.sqrt(1 - phi ** 2))
    for i in range(1, n):
        u[i] = phi * u[i - 1] + rng.normal(0, sd)
    return u


def coverage(phi, reps=400, n_boot=500, per_week=20, shock_sd=0.5):
    aw = season_weeks()
    hits = {(m, L): 0 for m in ("calendar", "active") for L in (1, 2, 4, 8, 12)}
    rej = {"lag0": 0, "hac_auto": 0}
    for r in range(reps):
        rng = np.random.default_rng(20000 + r)
        u = ar1(len(aw), phi, shock_sd, rng) if phi > 0 else rng.normal(0, shock_sd, len(aw))
        weeks = np.repeat(aw, per_week)
        d = np.repeat(u, per_week) + rng.normal(0, 1.0, weeks.size)
        for (m, L) in hits:
            b = ev.block_bootstrap_mean(d, weeks, block=L, n_boot=n_boot, seed=r, week_mode=m)
            hits[(m, L)] += b["lo"] <= 0 <= b["hi"]
        rej["lag0"] += ev.diebold_mariano(d, weeks, lag=0)["p_value"] < 0.05
        rej["hac_auto"] += ev.diebold_mariano(d, weeks)["p_value"] < 0.05
    return {"phi": phi, "reps": reps, "n_boot": n_boot,
            "coverage_95": {f"{m}_block{L}": h / reps for (m, L), h in hits.items()},
            "dm_rejection_rate_at_5pct": {k: v / reps for k, v in rej.items()}}


def validation_examples():
    cases = {"p>1": ([1, 0], [0.5, 1.2]), "p<0": ([1, 0], [0.5, -0.1]), "p=inf": ([1, 0], [0.5, np.inf]),
             "p=NaN": ([1, 0], [0.5, np.nan]), "y=2": ([1, 2], [0.5, 0.5]), "longitudes": ([1, 0, 1], [0.5, 0.5]),
             "p=1,y=0 (pérdida infinita)": ([0], [1.0])}
    out = {}
    for k, (y, p) in cases.items():
        try:
            ev.log_loss(y, p)
            out[k] = "ACEPTADO (error)"
        except InputValidationError as e:
            out[k] = f"rechazado: {e}"
    return out


def main():
    res = {"design": "6 temporadas de 38 semanas activas + 14 de pausa; 20 partidos por semana; d = u_semana + e, "
                     "e ~ N(0,1), u AR(1) con sd de innovación 0,5; media real 0",
           "dependent_phi_0.7": coverage(0.7), "independent_weeks": coverage(0.0),
           "validation_rejections": validation_examples(),
           "power_example": {"se_0.0003": ev.power_profile(0.0003, 0.001), "se_0.0008": ev.power_profile(0.0008, 0.001)}}
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float))
    print(json.dumps({k: v for k, v in res.items() if k != "power_example"}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

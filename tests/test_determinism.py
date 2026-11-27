"""Reproducibilidad entre procesos con distintos PYTHONHASHSEED (corrección previa a GATE 3).

El prior de ascendidos de M2 promediaba sobre un `set` de nombres de equipos, cuyo orden de iteración depende
de PYTHONHASHSEED; la suma en coma flotante dependía de ese orden (REPRODUCIBILITY_REPORT.md §3.2). Con
`sorted(departed)` el resultado debe ser idéntico bit a bit con cualquier semilla. Comprobado: con el código
antiguo la prueba sintética falla (diferencias de 2,2·10⁻¹⁶ entre semillas).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SEEDS = ("0", "1", "2", "3")

SYNTHETIC = r'''
import sys
import numpy as np
from qsports import models, synthetic, walkforward as wf
df = synthetic.generate(n_divisions=1, n_teams=14, seasons=("0506", "0607", "0708"), seed=31)
teams = sorted(set(df.home_team))
ren = {t: f"Nuevo{i}" for i, t in enumerate(teams[:5])}  # 5 descensos y 5 ascensos en 0708
m = df.season_code == "0708"
for c in ("home_team", "away_team"):
    df.loc[m, c] = df.loc[m, c].replace(ren)
p, logs = wf.run(df, lambda: models.PoissonModel(half_life_days=240, ridge=4.0, promoted_prior=True), ["0708"],
                 scope="division", label="pp", n_jobs=1, columns=["home_team", "away_team", "fthg", "ftag"])
assert logs["extra"].str.contains('"new_prior_att": 0.0,').sum() < len(logs)  # el prior se activó
np.save(sys.argv[1], p.sort_values("match_id")["p_over"].to_numpy())
'''

REAL = r'''
import sys, json
import numpy as np
from qsports import gate2, models, walkforward as wf
base = gate2.base_frame()
prm = {"half_life_days": 480, "ridge": 64.0, "max_history_days": 1460, "promoted_prior": True}
f = base[base["div"] == "T1"]
p, _ = wf.run(f, lambda: models.PoissonModel(**prm), gate2.cfg()["blocks"]["tuning_seasons_poisson"],
              scope="division", label="pp", n_jobs=1, columns=["home_team", "away_team", "fthg", "ftag"])
np.save(sys.argv[1], p.sort_values("match_id")["p_over"].to_numpy())
'''


def _run(code, out, seed):
    env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(ROOT / "src"), "OPENBLAS_NUM_THREADS": "1",
           "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
    r = subprocess.run([sys.executable, "-c", code, str(out)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    return np.load(out)


def test_promoted_prior_identical_across_hash_seeds_synthetic(tmp_path):
    res = [_run(SYNTHETIC, tmp_path / f"s{s}.npy", s) for s in SEEDS]
    for r in res[1:]:
        assert np.array_equal(r, res[0]), float(np.max(np.abs(r - res[0])))


def test_promoted_prior_identical_across_hash_seeds_real_data(tmp_path):
    """Caso real que reveló el defecto (división T1, M2 h480 r64 con prior de ascendidos)."""
    from qsports import paths
    if not (paths.PROCESSED_DEV / "matches.parquet").exists():
        pytest.skip("Requiere los datos de desarrollo (python -m qsports build)")
    res = [_run(REAL, tmp_path / f"r{s}.npy", s) for s in SEEDS[:3]]
    for r in res[1:]:
        assert np.array_equal(r, res[0]), float(np.max(np.abs(r - res[0])))

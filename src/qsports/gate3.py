"""GATE 3: validación histórica 2022/23-2023/24 de los candidatos CONGELADOS (una sola evaluación).

Garantías (probadas en tests/test_gate3.py):
1. Autorización: `walkforward.gate3_authorization()` (archivo del usuario ligado al SHA-256 de
   configs/gate3_frozen_candidates.json). Sin ella, ni el motor ni el universo de evaluación cruzan la valla.
2. Identidad de los candidatos, no solo el hash del documento:
   - el archivo congelado fija familia, config_id, clase y TODOS los argumentos del constructor;
   - deben coincidir con el registro (configs.json) y con las selecciones (results.json) de la
     reproducción limpia de referencia, cuyo RUN_MANIFEST debe ser limpio y con el mismo hash de código;
   - el código actual debe tener el hash congelado (sin cambios desde el congelamiento);
   - los modelos se construyen SOLO desde el archivo congelado y se comprueban sus atributos;
   - las entradas (predicciones de M2* de ajuste y prueba interna usadas para entrenar M4) deben tener
     el SHA-256 congelado;
   - réplica de identidad: los candidatos congelados, aplicados de nuevo a la prueba interna (desarrollo),
     deben reproducir bit a bit las predicciones de la reproducción de referencia.
3. Una sola evaluación: el directorio de salida no puede existir; al terminar se escribe un sello.
4. Protocolo estadístico congelado (δ, bootstrap, comparaciones) leído del archivo congelado.
"""
from __future__ import annotations

import datetime as dt
import json
from functools import partial
from pathlib import Path

import numpy as np
import pandas as pd

from . import evaluation as ev
from . import gate2, models, paths, validation as val, walkforward as wf

FROZEN_REL = "configs/gate3_frozen_candidates.json"
MODEL_CLASSES = {"PoissonModel": models.PoissonModel, "MarketModel": models.MarketModel}
POISSON_ATTRS = ("window_days", "half_life_days", "ridge", "max_history_days", "promoted_prior")
MARKET_ATTRS = ("sport_cols", "ridge", "half_life_days", "require_cols", "market_col")
# Valores con que las fábricas de GATE 2 (experiments/gate2/run.py, stage_m4) completaban los parámetros del registro.
GATE2_FACTORY_DEFAULTS = {"sport_cols": [], "ridge": 100.0, "market_col": "p_A_consensus"}


class CandidateIdentityError(RuntimeError):
    """Los candidatos o sus entradas no coinciden con lo congelado."""


class SingleEvaluationError(RuntimeError):
    """GATE 3 ya se evaluó (una sola evaluación)."""


def frozen_path() -> Path:
    return paths.ROOT / wf.gate2_config()["gate3_fence"]["frozen_candidates_file"]


def load_frozen() -> dict:
    p = frozen_path()
    if not p.exists():
        raise CandidateIdentityError(f"No existe {FROZEN_REL}: los candidatos no están congelados.")
    return json.loads(p.read_text())


def _norm(v):
    """Normaliza números (64 == 64.0) y listas para comparar parámetros."""
    if isinstance(v, bool) or v is None or isinstance(v, str):
        return v
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v)
    if isinstance(v, (list, tuple)):
        return [_norm(x) for x in v]
    if isinstance(v, dict):
        return {k: _norm(x) for k, x in v.items()}
    return v


def build_factory(spec: dict):
    """Fábrica construida SOLO desde la especificación congelada; comprueba los atributos del modelo."""
    cls = MODEL_CLASSES.get(spec["model"])
    if cls is None:
        raise CandidateIdentityError(f"Clase de modelo no permitida: {spec['model']}")
    args = spec["constructor_args"]
    attrs = POISSON_ATTRS if cls is models.PoissonModel else MARKET_ATTRS
    unknown = set(args) - set(attrs)
    if unknown:
        raise CandidateIdentityError(f"{spec['config_id']}: argumentos no reconocidos {sorted(unknown)}")
    m = cls(**args)
    for a, v in args.items():
        if _norm(getattr(m, a)) != _norm(v):
            raise CandidateIdentityError(f"{spec['config_id']}: {a} = {getattr(m, a)!r}, congelado {v!r}")
    return partial(cls, **args)


def verify_frozen(frozen: dict, require_authorization: bool = True) -> dict:
    """Comprobaciones de identidad previas a la evaluación. Devuelve un informe; lanza ante cualquier fallo."""
    rep: dict = {}
    if require_authorization:
        auth = wf.gate3_authorization()  # lanza FenceError si falta o no coincide el hash del archivo congelado
        rep["authorization"] = {k: auth[k] for k in ("authorized_by", "authorized_at", "frozen_candidates_sha256")}
    if frozen.get("code_hash") != gate2.code_hash():
        raise CandidateIdentityError("El código cambió desde el congelamiento (hash de código distinto).")
    rep["code_hash"] = frozen["code_hash"]
    ref = paths.ROOT / frozen["reference_run"]["dir"]
    man = json.loads((ref / "RUN_MANIFEST.json").read_text())
    if not (man.get("clean") and man.get("git_dirty") is False):
        raise CandidateIdentityError("La reproducción de referencia no fue una ejecución limpia sobre un árbol limpio.")
    if man.get("code_hash") != frozen["code_hash"] or man.get("git_commit") != frozen["reference_run"]["git_commit"]:
        raise CandidateIdentityError("La reproducción de referencia no corresponde al código/commit congelado.")
    reg = json.loads((ref / "configs.json").read_text())
    res = json.loads((ref / "results.json").read_text())
    selected = {"M2": res["poisson_tuning"]["M2_selected"], "M4cal": res["m4"]["M4cal_selected"],
                "M4sport": res["m4"]["M4sport_selected"]}
    if set(frozen["candidates"]) != set(selected):
        raise CandidateIdentityError(f"Candidatos congelados {sorted(frozen['candidates'])} != {sorted(selected)}")
    for name, spec in frozen["candidates"].items():
        if spec["config_id"] != selected[name]:
            raise CandidateIdentityError(f"{name}: congelado {spec['config_id']} != seleccionado {selected[name]}")
        rparams = reg[spec["config_id"]]["params"]
        for k, v in spec["constructor_args"].items():  # argumentos ausentes del registro: solo los valores que usó GATE 2
            if k not in rparams and (k not in GATE2_FACTORY_DEFAULTS or _norm(v) != _norm(GATE2_FACTORY_DEFAULTS[k])):
                raise CandidateIdentityError(f"{name}: {k}={v!r} no consta en el registro ni es el valor usado en GATE 2")
        for k, v in rparams.items():
            if k in spec["constructor_args"] and _norm(spec["constructor_args"][k]) != _norm(v):
                raise CandidateIdentityError(f"{name}: {k} congelado {spec['constructor_args'][k]!r} != registro {v!r}")
            if k not in spec["constructor_args"]:
                raise CandidateIdentityError(f"{name}: el registro tiene {k} y el archivo congelado no")
        build_factory(spec)
    if _norm(res["m4"]["sport_cols"]) != _norm(frozen["candidates"]["M4sport"]["constructor_args"]["sport_cols"]):
        raise CandidateIdentityError("sport_cols de M4-sport no coincide con la selección")
    for rel, sha in frozen["input_files_sha256"].items():
        if gate2.sha256_file(paths.ROOT / rel) != sha:
            raise CandidateIdentityError(f"Entrada alterada: {rel}")
    pr = frozen["protocol"]
    cfg = wf.gate2_config()
    if pr["sesoi_nats"] != cfg["sesoi_nats"] or pr["bootstrap"]["week_mode"] != "calendar":
        raise CandidateIdentityError("El protocolo congelado no coincide con el vigente")
    rep["candidates"] = {n: s["config_id"] for n, s in frozen["candidates"].items()}
    rep["reference_run"] = frozen["reference_run"]
    return rep


def freeze(reference_dir: Path, out: Path | None = None) -> dict:
    """Escribe configs/gate3_frozen_candidates.json desde una reproducción limpia de referencia (no sobrescribe)."""
    out = out or frozen_path()
    if out.exists():
        raise SingleEvaluationError(f"{out} ya existe: los candidatos ya están congelados.")
    ref = Path(reference_dir).resolve()
    man = json.loads((ref / "RUN_MANIFEST.json").read_text())
    if man.get("code_hash") != gate2.code_hash():
        raise CandidateIdentityError("La reproducción de referencia no se hizo con el código actual.")
    reg = json.loads((ref / "configs.json").read_text())
    res = json.loads((ref / "results.json").read_text())
    cfg = wf.gate2_config()
    m2, m4c, m4s = res["poisson_tuning"]["M2_selected"], res["m4"]["M4cal_selected"], res["m4"]["M4sport_selected"]
    sport = res["m4"]["sport_cols"]
    p2, pc, ps = reg[m2]["params"], reg[m4c]["params"], reg[m4s]["params"]
    every_l = cfg["refit"]["logistic_every_n_captures"]
    cands = {
        "M2": {"family": "M2", "config_id": m2, "model": "PoissonModel",
               "constructor_args": {"half_life_days": p2["half_life_days"], "ridge": float(p2["ridge"]),
                                    "max_history_days": p2["max_history_days"], "promoted_prior": p2["promoted_prior"]},
               "scope": "division", "refit_every": cfg["refit"]["poisson_every_n_captures"],
               "columns": ["home_team", "away_team", "fthg", "ftag"]},
        "M4cal": {"family": "M4cal", "config_id": m4c, "model": "MarketModel",
                  "constructor_args": {"sport_cols": [], "ridge": float(pc.get("ridge", 100.0)),
                                       "half_life_days": pc["half_life_days"], "require_cols": pc["require_cols"],
                                       "market_col": "p_A_consensus"},
                  "scope": "pooled", "refit_every": every_l, "columns": ["p_A_consensus", "over25"] + sport,
                  "inputs": {"inp_m2": "M2"}},
        "M4sport": {"family": "M4sport", "config_id": m4s, "model": "MarketModel",
                    "constructor_args": {"sport_cols": ps["sport_cols"], "ridge": float(ps["ridge"]),
                                         "half_life_days": ps["half_life_days"], "require_cols": ps["require_cols"],
                                         "market_col": "p_A_consensus"},
                    "scope": "pooled", "refit_every": every_l, "columns": ["p_A_consensus", "over25"] + sport,
                    "inputs": {"inp_m2": "M2"}},
    }
    inputs = {}
    for blk in ("tuning", "inner"):
        for ext in ("parquet", "json"):
            f = ref / "predictions" / "M2" / f"{m2}__{blk}.{ext}"
            inputs[str(f.relative_to(paths.ROOT))] = gate2.sha256_file(f)
    bs = cfg["selection"]["bootstrap"]
    frozen = {
        "_doc": ("Candidatos CONGELADOS para GATE 3 (validación 2022/23-2023/24, una sola evaluación). Creado por "
                 "instrucción expresa del usuario. El ejecutor (qsports.gate3) verifica identidad e hiperparámetros "
                 "frente a la reproducción de referencia y frente a los modelos instanciados."),
        "frozen_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "validation_seasons": ["2223", "2324"],
        "reference_run": {"dir": str(ref.relative_to(paths.ROOT)), "git_commit": man["git_commit"]},
        "code_hash": gate2.code_hash(),
        "candidates": cands,
        "input_files_sha256": inputs,
        "benchmarks": {"A": "p_A_consensus", "C": "p_C_hist_freq"},
        "universe": "temporadas de validación, resultado conocido, captura estimable, elig_A",
        "protocol": {"sesoi_nats": cfg["sesoi_nats"],
                     "bootstrap": {"week_mode": "calendar", "block_weeks": bs["block_weeks"],
                                   "n_boot": bs["n_boot_inner"], "seed": bs["seed"]},
                     "sensitivity_block_weeks": bs["sensitivity_block_weeks"],
                     "decision_partition": "EXPERIMENTAL_PROTOCOL.md §6 (S-R, S-NR, EQ, INC, I-NR, I-R)",
                     "primary_comparison": "M4sport-M4cal",
                     "comparisons": [["M4sport", "M4cal"], ["M4sport", "A"], ["M4cal", "A"], ["M2", "A"],
                                     ["M2", "C"], ["A", "C"]],
                     "per_season": True,
                     "q2_validity_condition_1": "Δ̄ < 0 de M4-sport frente a A en la validación (dirección consistente)"},
    }
    out.write_text(json.dumps(frozen, indent=1, ensure_ascii=False) + "\n")
    return frozen


# ---------------------------------------------------------------- ejecución
def _m4_frame(base, inp2):
    f = val.merge_one_to_one(base, inp2, context="gate3:inp_m2")
    f.index = base.index
    return f


def identity_replay(frozen: dict, base: pd.DataFrame) -> dict:
    """Aplica los candidatos congelados a la prueba INTERNA (desarrollo, dentro de la valla) y exige igualdad bit a
    bit con la reproducción de referencia. Prueba efectiva de que son los mismos modelos con los mismos parámetros."""
    cfg = wf.gate2_config()
    inner = cfg["blocks"]["inner_test_seasons"]
    ref = paths.ROOT / frozen["reference_run"]["dir"]
    c = frozen["candidates"]

    def ref_preds(name, blk):
        return pd.read_parquet(ref / "predictions" / c[name]["family"] / f"{c[name]['config_id']}__{blk}.parquet")

    out = {}
    m2 = c["M2"]
    p2, _ = wf.run(base, build_factory(m2), inner, scope=m2["scope"], refit_every=m2["refit_every"],
                   label="gate3-identity-M2", n_jobs=gate2.N_JOBS, columns=m2["columns"])
    inp2 = pd.concat([ref_preds("M2", "tuning"), ref_preds("M2", "inner")])[["match_id", "p_over"]].rename(
        columns={"p_over": "inp_m2"})
    frame = _m4_frame(base, inp2)
    preds = {"M2": p2}
    for name in ("M4cal", "M4sport"):
        s = c[name]
        preds[name], _ = wf.run(frame, build_factory(s), inner, scope=s["scope"], refit_every=s["refit_every"],
                                label=f"gate3-identity-{name}", n_jobs=1, columns=s["columns"])
    for name, p in preds.items():
        r = ref_preds(name, "inner")
        m = val.merge_one_to_one(r[["match_id", "p_over"]], p[["match_id", "p_over"]].rename(columns={"p_over": "new"}),
                                 how="outer", context=f"identity:{name}")
        eq = (m["p_over"] == m["new"]) | (m["p_over"].isna() & m["new"].isna())
        out[name] = {"rows": int(len(m)), "bitwise_equal": int(eq.sum()), "not_equal": int((~eq).sum())}
        if (~eq).any():
            raise CandidateIdentityError(f"Réplica de identidad fallida para {name}: {int((~eq).sum())} filas distintas")
    return out


def seal_path() -> Path:
    return paths.ROOT / "logs" / "GATE3_EVALUATED.json"


def run(out_dir: Path) -> dict:
    """Ejecuta la validación de GATE 3 UNA sola vez."""
    out_dir = Path(out_dir).resolve()
    if out_dir.exists():
        raise SingleEvaluationError(f"{out_dir} ya existe: GATE 3 admite una sola evaluación.")
    seal = seal_path()
    if seal.exists():
        raise SingleEvaluationError(f"{seal} existe: GATE 3 ya se evaluó.")
    frozen = load_frozen()
    report = {"started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "verification": verify_frozen(frozen)}
    base = gate2.base_frame()
    report["identity_replay_inner"] = identity_replay(frozen, base)
    out_dir.mkdir(parents=True)
    seas = frozen["validation_seasons"]
    c = frozen["candidates"]
    ref = paths.ROOT / frozen["reference_run"]["dir"]
    m2 = c["M2"]
    p2, l2 = wf.run(base, build_factory(m2), seas, scope=m2["scope"], refit_every=m2["refit_every"], label="gate3-M2",
                    n_jobs=gate2.N_JOBS, columns=m2["columns"])
    hist = pd.concat([pd.read_parquet(ref / "predictions" / "M2" / f"{m2['config_id']}__{b}.parquet")
                      for b in ("tuning", "inner")])
    inp2 = pd.concat([hist[["match_id", "p_over"]], p2[["match_id", "p_over"]]]).rename(columns={"p_over": "inp_m2"})
    frame = _m4_frame(base, inp2)
    preds, logs = {"M2": p2}, {"M2": l2}
    for name in ("M4cal", "M4sport"):
        s = c[name]
        preds[name], logs[name] = wf.run(frame, build_factory(s), seas, scope=s["scope"], refit_every=s["refit_every"],
                                         label=f"gate3-{name}", n_jobs=1, columns=s["columns"])
    for name in preds:
        p = preds[name].drop(columns=[x for x in ("train_max_date", "n_train") if x in preds[name].columns])
        p.to_parquet(out_dir / f"predictions_{name}.parquet", index=False)
        logs[name].to_parquet(out_dir / f"fitlogs_{name}.parquet", index=False)
    report["evaluation"] = evaluate(frozen, base, preds)
    report["fits"] = {n: {"n_fits": int(len(l)), "nonconverged": int((~l["converged"]).sum())} for n, l in logs.items()}
    report["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    report["artifacts_sha256"] = {f.name: gate2.sha256_file(f) for f in sorted(out_dir.glob("*.parquet"))}
    (out_dir / "results.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=float))
    seal.write_text(json.dumps({"evaluated_utc": report["finished_utc"], "out_dir": str(out_dir.relative_to(paths.ROOT)),
                                "results_sha256": gate2.sha256_file(out_dir / "results.json"),
                                "frozen_candidates_sha256": gate2.sha256_file(frozen_path())}, indent=1))
    return report


def evaluate(frozen: dict, base: pd.DataFrame, preds: dict) -> dict:
    pr = frozen["protocol"]
    seas = frozen["validation_seasons"]
    U = gate2.universe(base, seas, "elig_A")  # la valla se comprueba y registra aquí también
    S = U[["match_id", "match_date", "season_code", "over25", "p_A_consensus", "p_C_hist_freq"]].rename(
        columns={"p_A_consensus": "A", "p_C_hist_freq": "C"})
    cov = {}
    for name, p in preds.items():
        cov[name] = val.require_full_coverage(p, U, f"gate3:{name}")
        S = val.merge_one_to_one(S, p[["match_id", "p_over"]].rename(columns={"p_over": name}), context=f"gate3:{name}")
    for b in ("A", "C"):
        val.probabilities(S[b].to_numpy(), b)
    bs = pr["bootstrap"]
    out = {"n": int(len(S)), "seasons": seas, "universe": frozen["universe"], "coverage": cov, "delta": pr["sesoi_nats"],
           "bootstrap": bs, "describe": {k: ev.describe_forecast(S.over25, S[k]) for k in ("A", "C", "M2", "M4cal", "M4sport")}}
    comps, sens, per_season = {}, {}, {}
    for a, b in pr["comparisons"]:
        k = f"{a}-{b}"
        comps[k] = ev.compare(S.over25, S[a], S[b], S.match_date, pr["sesoi_nats"], n_boot=bs["n_boot"], seed=bs["seed"],
                              block=bs["block_weeks"], week_mode=bs["week_mode"])
        rows = []
        for L in pr["sensitivity_block_weeks"]:
            r = ev.compare(S.over25, S[a], S[b], S.match_date, pr["sesoi_nats"], n_boot=bs["n_boot"], seed=bs["seed"],
                           block=L, week_mode="calendar")
            rows.append({"block_weeks": L, "lo": r["delta_logloss"]["lo"], "hi": r["delta_logloss"]["hi"],
                         "category": r["category"]})
        d = ev.log_loss(S.over25, S[a]) - ev.log_loss(S.over25, S[b])
        sens[k] = {"rows": rows, "categories": sorted({r["category"] for r in rows}),
                   "weekly_autocorr_lags1_8": ev.weekly_autocorrelation(d, ev.week_ids(S.match_date), 8, "calendar")}
        per_season[k] = {sc: float((ev.log_loss(g.over25, g[a]) - ev.log_loss(g.over25, g[b])).mean())
                         for sc, g in S.groupby("season_code")}
    out.update(comparisons=comps, block_sensitivity=sens, per_season=per_season,
               reliability={k: ev.reliability_table(S.over25, S[k]).to_dict("records") for k in ("A", "M2", "M4cal", "M4sport")})
    m = comps["M4sport-A"]["delta_logloss"]["mean"]
    out["q2_validity_condition_1_direction"] = {"M4sport_minus_A_mean": m, "consistent_negative": bool(m < 0)}
    return out


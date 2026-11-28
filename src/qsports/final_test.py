"""Prueba final (holdout 2024/25-2025/26): ejecutor preparado en GATE 4. NO se ejecuta sin la autorización
expresa del usuario (HOLDOUT_AUTHORIZATION.json ligado al hash de PROTOCOL_FREEZE.json).

Candidato primario único: M4-cal h730, idéntico al congelado y evaluado en GATE 3. M2* se ejecuta solo como
auxiliar: define qué filas de entrenamiento tienen `inp_m2`, como en GATE 2-3. M4-cal no usa sus valores.

Controles (tests/test_final_test.py, solo con datos sintéticos):
1. Evaluación única: el directorio de salida no puede existir, ni el sello, ni el MARCADOR DE INTENTO. El marcador
   se crea de forma exclusiva (O_CREAT | O_EXCL) inmediatamente antes de abrir el holdout y nunca se borra: una
   interrupción posterior o una ejecución concurrente no permite un segundo intento automático. Los estados
   (inicio, apertura, finalización, interrupción) se anotan en un registro append-only.
2. Autorización del holdout verificada ANTES de cargar nada del holdout; la reserva nunca se admite.
3. Identidad: el candidato es exactamente el de GATE 3 (dict y SHA-256 del archivo congelado), con los mismos
   archivos de modelo, el mismo hash de código congelado y las mismas entradas; atributos instanciados verificados;
   réplica de identidad bit a bit en la prueba interna de desarrollo.
4. Datos: hash de contenido del desarrollo = el autorizado. Holdout: antes de abrirlo, el hash del registro debe
   ser igual al congelado en la especificación; tras cargarlo, su hash de contenido debe coincidir con AMBOS (registro
   y especificación). Benchmarks del desarrollo recalculados = los almacenados.
5. Protocolo congelado: δ = 0,001; bootstrap por bloques de 4 semanas calendario (10.000 réplicas, semilla fija);
   Q1 = M4-cal − C; Q2 = M4-cal − A con las tres condiciones de validez del protocolo §6; Q3 NO EVALUADA.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from . import benchmark, gate2, gate3, holdout, paths, process, validation as val, walkforward as wf
from . import evaluation as ev

SPEC_REL = "configs/final_test_frozen.json"
SEAL_REL = "logs/FINAL_TEST_EVALUATED.json"
ATTEMPT_REL = "logs/FINAL_TEST_ATTEMPT.json"      # marcador exclusivo de intento (permanente)
STATE_LOG_REL = "logs/FINAL_TEST_STATE_LOG.jsonl"  # registro append-only de estados
MODEL_FILES = ("src/qsports/models.py", "src/qsports/odds.py", "src/qsports/ou.py", "src/qsports/benchmark.py")
PURPOSE = "Prueba final preregistrada (FINAL_TEST_PROTOCOL.md): una sola evaluación de M4-cal h730"


class FinalTestError(RuntimeError):
    """Fallo de identidad, de datos o de protocolo en la prueba final."""


class DatasetHashError(FinalTestError):
    """El dataset cargado no es el autorizado."""


def spec_path() -> Path:
    return paths.ROOT / SPEC_REL


def seal_path() -> Path:
    return paths.ROOT / SEAL_REL


def attempt_path() -> Path:
    return paths.ROOT / ATTEMPT_REL


def state_log_path() -> Path:
    return paths.ROOT / STATE_LOG_REL


def log_state(state: str, **info) -> None:
    """Registro append-only de estados de la prueba final: started, opened, finished, interrupted."""
    p = state_log_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps({"at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "state": state, **info},
                           ensure_ascii=False, default=str) + "\n")
        f.flush()
        os.fsync(f.fileno())


def read_states() -> list[dict]:
    p = state_log_path()
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def claim_attempt(info: dict) -> None:
    """Crea el marcador de intento de forma EXCLUSIVA y persistente. Si ya existe (intento previo interrumpido o
    ejecución concurrente), lanza SingleEvaluationError: no hay reintentos automáticos."""
    p = attempt_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError as e:
        raise gate3.SingleEvaluationError(
            f"{p} existe: ya hubo un intento de prueba final (posiblemente interrumpido o concurrente). No se permiten "
            f"reintentos automáticos; cualquier decisión corresponde al usuario.") from e
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps({"claimed_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "pid": os.getpid(), **info},
                           ensure_ascii=False, indent=1, default=str))
        f.flush()
        os.fsync(f.fileno())


def load_spec() -> dict:
    if not spec_path().exists():
        raise FinalTestError(f"No existe {SPEC_REL}: la prueba final no está congelada.")
    return json.loads(spec_path().read_text())


# ---------------------------------------------------------------- veredictos (protocolo §6)
def q1_verdict(category: str) -> dict:
    if category == "S-R":
        return {"verdict": "AFIRMATIVO", "reading": "mejora relevante sobre una referencia simple"}
    if category == "S-NR":
        return {"verdict": "AFIRMATIVO", "reading": "mejora estadística de magnitud incierta"}
    if category in ("EQ", "I-NR", "I-R"):
        return {"verdict": "NEGATIVO", "reading": "no mejora a una referencia simple"}
    if category == "INC":
        return {"verdict": "EVIDENCIA INSUFICIENTE", "reading": "inconcluso"}
    raise ValueError(category)


def q2_verdict(category: str, conditions: dict[str, bool]) -> dict:
    failed = [k for k, v in conditions.items() if not v]
    if category in ("S-R", "S-NR"):
        if failed:
            return {"verdict": "VENTAJA ESTADÍSTICA NO DEMOSTRADA", "category": category, "failed_conditions": failed,
                    "reading": "superioridad estadística, pero falla una condición de validez"}
        return {"verdict": "AFIRMATIVO", "category": category,
                "reading": ("superioridad estadística y relevante" if category == "S-R"
                            else "superioridad estadística; relevancia (> δ) no demostrada")}
    if category in ("EQ", "I-NR", "I-R"):
        return {"verdict": "VENTAJA ESTADÍSTICA NO DEMOSTRADA", "category": category, "failed_conditions": failed}
    if category == "INC":
        return {"verdict": "VENTAJA ESTADÍSTICA NO DEMOSTRADA / EVIDENCIA INSUFICIENTE", "category": category,
                "failed_conditions": failed}
    raise ValueError(category)


def superiority_levels(lo: float, hi: float, delta: float) -> dict:
    """Distingue superioridad estadística (U < 0), superioridad relevante (U < −δ) y rentabilidad (no evaluada)."""
    return {"statistical_superiority": bool(hi < 0), "relevant_superiority": bool(hi < -delta),
            "profitability": "NO EVALUADA (Q3: protocolo económico separado, exclusivamente simulado)"}


# ---------------------------------------------------------------- identidad
def verify_spec(spec: dict, require_inputs: bool = True) -> dict:
    """Comprobaciones de identidad contra el repositorio (sin datos del holdout)."""
    rep: dict = {}
    if spec.get("code_hash") != gate2.code_hash():
        raise FinalTestError("El código cambió desde el congelamiento de la prueba final (hash de código distinto).")
    for rel, sha in spec["model_files_sha256"].items():
        if gate2.sha256_file(paths.ROOT / rel) != sha:
            raise FinalTestError(f"Archivo de modelo modificado: {rel}")
    g3 = paths.ROOT / spec["gate3_frozen"]["file"]
    if gate2.sha256_file(g3) != spec["gate3_frozen"]["sha256"]:
        raise FinalTestError("El archivo congelado de GATE 3 cambió.")
    g3c = json.loads(g3.read_text())["candidates"]
    if spec["primary"] != g3c["M4cal"]:
        raise FinalTestError("El candidato primario no es exactamente M4-cal de GATE 3.")
    if spec["auxiliary_M2"] != g3c["M2"]:
        raise FinalTestError("El auxiliar M2 no es exactamente M2* de GATE 3.")
    gate3.build_factory(spec["primary"])
    gate3.build_factory(spec["auxiliary_M2"])
    if spec["protocol"]["sesoi_nats"] != wf.gate2_config()["sesoi_nats"] or spec["protocol"]["sesoi_nats"] != 0.001:
        raise FinalTestError("SESOI distinto de 0,001 nats.")
    if spec["holdout_seasons"] != paths.holdout_config()["holdout_seasons"]:
        raise FinalTestError("Temporadas del holdout distintas de las selladas.")
    reg = holdout.registry("holdout")  # nivel 0: no abre el holdout
    if spec["dataset"].get("holdout_full_content_sha256_sealed") != reg["full_content_sha256"]:
        raise FinalTestError("El hash sellado del holdout en la especificación no coincide con el registro.")
    missing = []
    for rel, sha in spec["input_files_sha256"].items():
        p = paths.ROOT / rel
        if not p.exists():
            missing.append(rel)
        elif gate2.sha256_file(p) != sha:
            raise FinalTestError(f"Entrada alterada: {rel}")
    if missing and require_inputs:
        raise FinalTestError(f"Faltan entradas congeladas: {missing}")
    rep.update(code_hash=spec["code_hash"], primary=spec["primary"]["config_id"],
               auxiliary=spec["auxiliary_M2"]["config_id"], missing_inputs=missing)
    return rep


def verify_dev_dataset(spec: dict, dev: pd.DataFrame, bench: pd.DataFrame) -> dict:
    got = {"dev_matches_content_sha256": holdout.content_hash(dev),
           "dev_benchmarks_content_sha256": holdout.content_hash(bench)}
    for k, v in got.items():
        if v != spec["dataset"][k]:
            raise DatasetHashError(f"Dataset de desarrollo distinto del autorizado ({k}).")
    return got


# ---------------------------------------------------------------- datos
class RealData:
    """Datos reales: desarrollo con load_dev, holdout con load_authorized_holdout (tras autorización)."""

    def __init__(self, spec: dict):
        self.spec = spec

    def dev_frames(self):
        return process.load_dev(), process.load_dev_benchmarks()

    def _read(self, rel):
        return pd.read_parquet(paths.ROOT / rel)

    def dev_inp_m2(self) -> pd.DataFrame:
        parts = [self._read(r)[["match_id", "p_over"]] for r in self.spec["inputs_dev_inp_m2"]]
        return pd.concat(parts, ignore_index=True).rename(columns={"p_over": "inp_m2"})

    def identity_reference(self) -> dict:
        r = self.spec["identity_reference"]
        return {"seasons": r["seasons"], "inp_m2": self._read_many(r["inp_m2_files"]),
                "preds": {k: self._read(v)[["match_id", "p_over"]] for k, v in r["pred_files"].items()}}

    def _read_many(self, rels):
        return pd.concat([self._read(x)[["match_id", "p_over"]] for x in rels], ignore_index=True).rename(
            columns={"p_over": "inp_m2"})

    def registry_holdout_hash(self) -> str:
        """Hash de contenido sellado del registro (nivel 0; no abre el holdout)."""
        return holdout.registry("holdout")["full_content_sha256"]

    def load_holdout(self, purpose: str):
        df, meta = holdout.load_authorized_holdout(purpose)
        return df, meta["full_content_sha256"]


def base_from(dev: pd.DataFrame, bench: pd.DataFrame) -> pd.DataFrame:
    """Marco de desarrollo exactamente como gate2.base_frame (benchmarks almacenados)."""
    d = dev.copy()
    val.unique_ids(d, "match_id", "dev")
    if not (d["match_id"].values == bench["match_id"].values).all():
        raise FinalTestError("benchmarks desalineados")
    for c in ["p_A_consensus", "A_consensus_valid", "p_C_hist_freq"]:
        d[c] = bench[c].values
    d["elig_A"] = (d["A_consensus_valid"].astype(bool) & ~d["capture_rule_ambiguous"].astype(bool)
                   & d["fthg"].notna() & ~d["duplicate_key"].astype(bool))
    return d


def combined_frame(dev: pd.DataFrame, bench: pd.DataFrame, hold: pd.DataFrame) -> pd.DataFrame:
    """Desarrollo + holdout con los benchmarks recalculados por el MISMO código sobre el conjunto combinado
    (point-in-time). Comprueba que en las filas de desarrollo coinciden con los almacenados."""
    h = hold.copy()
    if "date_in_season_window" in dev.columns and "date_in_season_window" not in h.columns:
        h["date_in_season_window"] = process.season_window_ok(h)
    comb = pd.concat([dev, h], ignore_index=True)
    val.unique_ids(comb, "match_id", "dev+holdout")
    b = benchmark.market_benchmarks(comb)
    comb["p_A_consensus"], comb["A_consensus_valid"] = b["p_A_consensus"].values, b["A_consensus_valid"].values
    comb["p_C_hist_freq"] = benchmark.historical_frequency(comb).values
    nd = len(dev)
    for c in ("p_A_consensus", "A_consensus_valid", "p_C_hist_freq"):
        a, s = comb[c].to_numpy()[:nd], bench[c].to_numpy()
        same = (a == s) | (pd.isna(a) & pd.isna(s))
        if not same.all():
            raise FinalTestError(f"Benchmark {c} recalculado distinto del almacenado en {int((~same).sum())} filas de desarrollo")
    comb["elig_A"] = (comb["A_consensus_valid"].astype(bool) & ~comb["capture_rule_ambiguous"].astype(bool)
                      & comb["fthg"].notna() & ~comb["duplicate_key"].astype(bool))
    return comb


def identity_replay(spec: dict, base: pd.DataFrame, ref: dict) -> dict:
    """M2 auxiliar y M4-cal, reconstruidos desde el archivo congelado, en temporadas de DESARROLLO: igualdad bit a bit."""
    seasons = ref["seasons"]
    m2, m4 = spec["auxiliary_M2"], spec["primary"]
    p2, _ = wf.run(base, gate3.build_factory(m2), seasons, scope=m2["scope"], refit_every=m2["refit_every"],
                   label="final-identity-M2", n_jobs=gate2.N_JOBS, columns=m2["columns"])
    frame = val.merge_one_to_one(base, ref["inp_m2"], context="final-identity:inp_m2")
    frame.index = base.index
    p4, _ = wf.run(frame, gate3.build_factory(m4), seasons, scope=m4["scope"], refit_every=m4["refit_every"],
                   label="final-identity-M4cal", n_jobs=1, columns=m4["columns"])
    out = {}
    for name, p in (("M2", p2), ("M4cal", p4)):
        r = ref["preds"][name]
        m = val.merge_one_to_one(r, p[["match_id", "p_over"]].rename(columns={"p_over": "new"}), how="outer",
                                 context=f"final-identity:{name}")
        eq = (m["p_over"] == m["new"]) | (m["p_over"].isna() & m["new"].isna())
        out[name] = {"rows": int(len(m)), "bitwise_equal": int(eq.sum()), "not_equal": int((~eq).sum())}
        if (~eq).any():
            raise FinalTestError(f"Réplica de identidad fallida para {name}: {int((~eq).sum())} filas distintas")
    return out


# ---------------------------------------------------------------- evaluación
def evaluate(spec: dict, frame: pd.DataFrame, preds: dict, auth: dict) -> dict:
    pr = spec["protocol"]
    seas = spec["holdout_seasons"]
    U = gate2.universe(frame, seas, "elig_A", holdout_authorization=auth)
    S = U[["match_id", "match_date", "season_code", "over25", "p_A_consensus", "p_C_hist_freq"]].rename(
        columns={"p_A_consensus": "A", "p_C_hist_freq": "C"})
    cov = {"M4cal": val.require_full_coverage(preds["M4cal"], U, "final:M4cal")}
    S = val.merge_one_to_one(S, preds["M4cal"][["match_id", "p_over"]].rename(columns={"p_over": "M4cal"}),
                             context="final:M4cal")
    for b in ("A", "C"):
        val.probabilities(S[b].to_numpy(), b)
    bs = pr["bootstrap"]
    d = pr["sesoi_nats"]
    out = {"n": int(len(S)), "seasons": seas, "coverage": cov, "delta": d, "bootstrap": bs,
           "describe": {k: ev.describe_forecast(S.over25, S[k]) for k in ("M4cal", "A", "C")}}
    comps, sens = {}, {}
    for q, (a, b) in (("Q1", ("M4cal", "C")), ("Q2", ("M4cal", "A"))):
        r = ev.compare(S.over25, S[a], S[b], S.match_date, d, n_boot=bs["n_boot"], seed=bs["seed"],
                       block=bs["block_weeks"], week_mode=bs["week_mode"])
        comps[q] = {"comparison": f"{a}-{b}", **r,
                    "levels": superiority_levels(r["delta_logloss"]["lo"], r["delta_logloss"]["hi"], d)}
        sens[q] = []
        for L in pr["sensitivity_block_weeks"]:
            rs = ev.compare(S.over25, S[a], S[b], S.match_date, d, n_boot=bs["n_boot"], seed=bs["seed"], block=L,
                            week_mode="calendar")
            sens[q].append({"block_weeks": L, "lo": rs["delta_logloss"]["lo"], "hi": rs["delta_logloss"]["hi"],
                            "category": rs["category"]})
    cal = out["describe"]["M4cal"]
    thr = pr["q2_conditions"]
    conditions = {
        "1_direccion_en_validacion": bool(thr["validation_M4cal_minus_A_mean"] < 0),
        "2_calibracion_en_holdout": bool(abs(cal["cal_slope"] - 1) < thr["calibration_slope_tolerance"]
                                         and abs(cal["cal_intercept_in_the_large"]) < thr["calibration_intercept_tolerance"]),
        "3_modelo_primario_unico": bool(spec.get("primary_count") == 1),
    }
    out.update(comparisons=comps, block_sensitivity=sens, q2_conditions=conditions,
               verdicts={"Q1": q1_verdict(comps["Q1"]["category"]),
                         "Q2": q2_verdict(comps["Q2"]["category"], conditions),
                         "Q3": {"verdict": "NO EVALUADA", "reading": "protocolo económico separado, exclusivamente simulado"}},
               per_season={q: {sc: float((ev.log_loss(g.over25, g[c[0]]) - ev.log_loss(g.over25, g[c[1]])).mean())
                               for sc, g in S.groupby("season_code")}
                           for q, c in (("Q1", ("M4cal", "C")), ("Q2", ("M4cal", "A")))})
    return out


# ---------------------------------------------------------------- ejecución única
def run_final(out_dir, data=None, spec: dict | None = None, verify_repo: bool = True) -> dict:
    """Ejecuta la prueba final UNA sola vez. En producción: run_final(out_dir) con los datos reales."""
    out_dir = Path(out_dir).resolve()
    if out_dir.exists():
        raise gate3.SingleEvaluationError(f"{out_dir} ya existe: la prueba final admite una sola evaluación.")
    if seal_path().exists():
        raise gate3.SingleEvaluationError(f"{seal_path()} existe: la prueba final ya se evaluó.")
    if attempt_path().exists():
        raise gate3.SingleEvaluationError(f"{attempt_path()} existe: ya hubo un intento de prueba final; no se reintenta.")
    auth = holdout.holdout_authorization()  # sin autorización válida, nada más se ejecuta
    spec = spec or load_spec()
    data = data or RealData(spec)
    report = {"started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "authorization": {k: auth[k] for k in ("authorized_by", "authorized_at", "protocol_freeze_sha256")}}
    if verify_repo:
        report["spec_verification"] = verify_spec(spec, require_inputs=True)
    dev, bench = data.dev_frames()
    report["dev_dataset"] = verify_dev_dataset(spec, dev, bench)
    base = base_from(dev, bench)
    report["identity_replay"] = identity_replay(spec, base, data.identity_reference())
    # A. Identidad del dataset reservado, ANTES de abrir: registro = especificación congelada
    sealed_spec = spec["dataset"]["holdout_full_content_sha256_sealed"]
    reg_hash = data.registry_holdout_hash()
    if reg_hash != sealed_spec:
        raise DatasetHashError("El hash sellado del registro del holdout no coincide con el de la especificación congelada.")
    # B. Marcador exclusivo y persistente inmediatamente antes de la apertura
    claim_attempt({"out_dir": str(out_dir), "protocol_freeze_sha256": auth["protocol_freeze_sha256"],
                   "holdout_full_content_sha256_sealed": sealed_spec})
    log_state("started", out_dir=str(out_dir), protocol_freeze_sha256=auth["protocol_freeze_sha256"])
    try:
        hold, expected = data.load_holdout(PURPOSE)
        got = holdout.content_hash(hold)
        if not (got == expected == reg_hash == sealed_spec):
            raise DatasetHashError("El holdout cargado no coincide con el hash sellado del registro y de la "
                                   "especificación congelada.")
        log_state("opened", rows=int(len(hold)), full_content_sha256=got)
        report["holdout_dataset"] = {"full_content_sha256": got, "rows": int(len(hold)),
                                     "matches_registry": got == expected, "matches_frozen_spec": got == sealed_spec}
        holdout.assert_no_reserved(hold, "final:holdout", allow_holdout=auth)
        frame = combined_frame(dev, bench, hold)
        seas = spec["holdout_seasons"]
        m2, m4 = spec["auxiliary_M2"], spec["primary"]
        p2, l2 = wf.run(frame, gate3.build_factory(m2), seas, scope=m2["scope"], refit_every=m2["refit_every"],
                        label="final-M2-aux", n_jobs=gate2.N_JOBS, columns=m2["columns"], holdout_authorization=auth)
        inp = pd.concat([data.dev_inp_m2(), p2[["match_id", "p_over"]].rename(columns={"p_over": "inp_m2"})],
                        ignore_index=True)
        f4 = val.merge_one_to_one(frame, inp, context="final:inp_m2")
        f4.index = frame.index
        p4, l4 = wf.run(f4, gate3.build_factory(m4), seas, scope=m4["scope"], refit_every=m4["refit_every"],
                        label="final-M4cal", n_jobs=1, columns=m4["columns"], holdout_authorization=auth)
        out_dir.mkdir(parents=True)
        for name, p, lg in (("M4cal", p4, l4), ("M2_aux", p2, l2)):
            p.drop(columns=[c for c in ("train_max_date", "n_train") if c in p.columns]).to_parquet(
                out_dir / f"predictions_{name}.parquet", index=False)
            lg.to_parquet(out_dir / f"fitlogs_{name}.parquet", index=False)
        report["evaluation"] = evaluate(spec, frame, {"M4cal": p4}, auth)
        report["fits"] = {n: {"n_fits": int(len(lg)), "nonconverged": int((~lg["converged"]).sum())}
                          for n, lg in (("M4cal", l4), ("M2_aux", l2))}
        report["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        report["artifacts_sha256"] = {f.name: gate2.sha256_file(f) for f in sorted(out_dir.glob("*.parquet"))}
        (out_dir / "results.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=float))
        seal_path().parent.mkdir(parents=True, exist_ok=True)
        seal_path().write_text(json.dumps({"evaluated_utc": report["finished_utc"], "out_dir": str(out_dir),
                                           "results_sha256": gate2.sha256_file(out_dir / "results.json"),
                                           "protocol_freeze_sha256": auth["protocol_freeze_sha256"]}, indent=1))
        log_state("finished", results_sha256=gate2.sha256_file(out_dir / "results.json"))
    except BaseException as e:  # incluye KeyboardInterrupt y SystemExit
        log_state("interrupted", error=type(e).__name__, message=str(e)[:500])
        raise
    return report


# ---------------------------------------------------------------- congelamiento (GATE 4)
def build_spec(power: dict | None = None) -> dict:
    """Especificación congelada de la prueba final a partir de GATE 3 (no sobrescribe)."""
    if spec_path().exists():
        raise gate3.SingleEvaluationError(f"{spec_path()} ya existe: la prueba final ya está congelada.")
    g3 = gate3.load_frozen()
    ref = g3["reference_run"]["dir"]
    res3 = json.loads((paths.ROOT / "experiments/gate3/validation_run/results.json").read_text())
    g3m = json.loads((paths.ROOT / "experiments/gate3/records/HASH_MANIFEST_GATE3.json").read_text())
    model_sha = {r: gate2.sha256_file(paths.ROOT / r) for r in MODEL_FILES}
    unchanged = {r: g3m["code"]["files_sha256"].get(r) == s for r, s in model_sha.items()}
    if not all(unchanged.values()):
        raise FinalTestError(f"Archivos de modelo distintos de GATE 3: {unchanged}")
    dev, bench = process.load_dev(), process.load_dev_benchmarks()
    reg = holdout.registry("holdout")
    m2id, m4id = g3["candidates"]["M2"]["config_id"], g3["candidates"]["M4cal"]["config_id"]
    inp_files = [f"{ref}/predictions/M2/{m2id}__tuning.parquet", f"{ref}/predictions/M2/{m2id}__inner.parquet",
                 "experiments/gate3/validation_run/predictions_M2.parquet"]
    id_preds = {"M2": f"{ref}/predictions/M2/{m2id}__inner.parquet",
                "M4cal": f"{ref}/predictions/M4cal/{m4id}__inner.parquet"}
    files = sorted(set(inp_files) | set(id_preds.values()))
    cfg = wf.gate2_config()
    bs = cfg["selection"]["bootstrap"]
    spec = {
        "_doc": ("Prueba final congelada en GATE 4 (holdout 2024/25-2025/26, una sola evaluación). Candidato primario "
                 "único M4-cal h730 seleccionado por el usuario, idéntico al de GATE 3. Abrir el holdout requiere "
                 "HOLDOUT_AUTHORIZATION.json, creado solo por instrucción expresa del usuario."),
        "frozen_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "holdout_seasons": paths.holdout_config()["holdout_seasons"],
        "primary": g3["candidates"]["M4cal"], "primary_count": 1, "auxiliary_M2": g3["candidates"]["M2"],
        "gate3_frozen": {"file": gate3.FROZEN_REL, "sha256": gate2.sha256_file(gate3.frozen_path())},
        "model_files_sha256": model_sha, "model_files_unchanged_since_gate3": unchanged,
        "code_hash": gate2.code_hash(),
        "dataset": {"dev_matches_content_sha256": holdout.content_hash(dev),
                    "dev_benchmarks_content_sha256": holdout.content_hash(bench), "dev_rows": int(len(dev)),
                    "holdout_full_content_sha256_sealed": reg["full_content_sha256"],
                    "holdout_level0_content_sha256": reg["level0_content_sha256"],
                    "holdout_raw_files_sha256": {k: v["sha256"] for k, v in reg["raw_files"].items()},
                    "holdout_n_matches_registry": reg["n_matches"]},
        "inputs_dev_inp_m2": inp_files,
        "identity_reference": {"seasons": cfg["blocks"]["inner_test_seasons"], "pred_files": id_preds,
                               "inp_m2_files": inp_files[:2]},
        "input_files_sha256": {f: gate2.sha256_file(paths.ROOT / f) for f in files},
        "universe": "temporadas del holdout, resultado conocido, captura estimable, elig_A (par promedio válido, "
                    "captura no ambigua, sin clave duplicada)",
        "protocol": {"sesoi_nats": cfg["sesoi_nats"],
                     "bootstrap": {"week_mode": "calendar", "block_weeks": bs["block_weeks"], "n_boot": bs["n_boot_inner"],
                                   "seed": bs["seed"]},
                     "sensitivity_block_weeks": bs["sensitivity_block_weeks"],
                     "decision_partition": "EXPERIMENTAL_PROTOCOL.md §6",
                     "Q1": "M4cal − C", "Q2": "M4cal − A", "Q3": "NO EVALUADA (protocolo económico separado)",
                     "q2_conditions": {"validation_M4cal_minus_A_mean":
                                       res3["evaluation"]["comparisons"]["M4cal-A"]["delta_logloss"]["mean"],
                                       "calibration_slope_tolerance": 0.2, "calibration_intercept_tolerance": 0.05,
                                       "single_primary_model": True}},
        "power": power or {},
    }
    spec_path().write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
    return spec

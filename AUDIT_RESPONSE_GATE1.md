# AUDIT_RESPONSE_GATE1 — Respuesta a la auditoría externa de GATE 1

Fecha: 2026-11-27 · Auditoría: informe externo (ChatGPT) entregado por el usuario ·
Decisión del usuario: GATE 1 aprobado; 2026/27 se mantiene sellada; los 4 alias se aceptan;
GATE 2 autorizado. El usuario aceptó las correcciones de esta respuesta.

## 1. Alcance de la auditoría
El auditor declaró que **no ejecutó el código** ni las pruebas. El informe es una
**revisión documental**, no una replicación independiente. Para GATE 3 se recomienda un
auditor que ejecute `python -m pytest` y `python -m qsports verify`, o el paquete de
auditoría sintético de GATE 2.

## 2. Correcciones a afirmaciones del informe

| Afirmación del informe | Corrección |
|---|---|
| "sha de árbol 512070e…" | `512070e` es el hash del **commit**; el del árbol es `2e1de5e…` |
| Los alias "se aplican solo dentro de la misma liga/año" | Se aplican **por país en todas las temporadas**: su objetivo es unificar la identidad de un club a lo largo del tiempo |
| "Un CLV positivo indica ineficiencias" | Indica haber batido el precio de cierre; no demuestra por sí solo una ineficiencia explotable |
| "Se usó un holdout estático; se recomienda validación rodante" | El protocolo ya especifica walk-forward con reajuste en cada captura. El holdout estático es solo la prueba final única |
| Referencias a un blog comercial (iSportsAPI) | No es una fuente científica. Las recomendaciones coinciden con la literatura (Gneiting y Raftery 2007; Walsh y Joshi 2024) |

## 3. Recomendaciones adoptadas (implementadas en GATE 2)

| Recomendación | Implementación | Prueba |
|---|---|---|
| Verificar exclusión de partidos del mismo día (jornadas nocturnas) | Ya existía; se añadió un caso explícito viernes 19:00 frente a 21:00 | `test_same_day_night_match_cannot_use_earlier_same_day_result` |
| Documentar el día de captura sin hora exacta | La captura depende solo de la fecha; la hora solo marca ambigüedad | `test_capture_day_independent_of_kickoff_hour` |
| Prueba de "migración de cuotas" (más días, más movimiento) | Prueba de regresión sobre desarrollo: vie < sáb < dom < lun y mar < mié | `test_pre_to_close_movement_gradient_regression` |
| Verificar que los alias no fusionan clubes distintos | Apariciones por división-temporada acotadas; ningún equipo juega contra sí mismo; alcance por país | `test_alias_integrity_no_merged_distinct_teams`, `test_alias_config_scope` |
| Pruebas de calibración, bootstrap y potencia | Evaluador con pruebas sobre datos sintéticos de propiedades conocidas | `tests/test_evaluation.py` (23 pruebas) |
| Pares O/U coherentes de la misma fuente y momento | Ya garantizado; ver `MARKET_BENCHMARK_SPECIFICATION.md` §1 y `test_max_pair_never_used_as_fair_probability` | — |
| Semillas fijas | Todas las rutinas aleatorias reciben semilla (`configs/gate2.json`) | — |

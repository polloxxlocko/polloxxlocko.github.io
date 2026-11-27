# GATE_2_1_REPORT — Fase correctiva tras la auditoría de GATE 2

Fecha: 2026-11-27 · Rama: `gate2.1` (no fusionada con `main`) · GATE 3: **no autorizado, no
iniciado** · Holdout y reserva: **sellados, 0 accesos registrados** · Bloque de validación
2022/23-2023/24: **vallado, 0 intentos registrados**

Documentos hermanos: `AUDIT_RESPONSE_GATE2.md` (respuesta punto por punto),
`REPRODUCIBILITY_REPORT.md` (reproducción limpia y comparación), `reports/gate2_1/TABLES.md`
(tablas generadas desde los JSON) y `reports/gate2_1/TEST_RECORD.md` (quién ejecutó qué).

⟦RESUMEN⟧

## 1. Qué se corrigió
| # | Exigencia | Corrección | Evidencia |
|---|---|---|---|
| 1 | Reproducibilidad real | Directorio por ejecución, `--clean`, cachés con manifiesto (clave + SHA-256), escrituras atómicas, `RUN_MANIFEST.json`, solo lectura de lo publicado, comparación fila a fila | `tests/test_gate2_cache.py`; `REPRODUCIBILITY_REPORT.md` |
| 2 | Evaluador | Semanas calendario explícitas (D-4), sensibilidad 2/4/8/12, autocorrelación semanal, potencia de superioridad frente a equivalencia, pruebas bajo dependencia serial | `tests/test_evaluation_v21.py`; `experiments/gate2_1/evaluator_evidence.json`; §3 |
| 3 | Validación de entradas | `qsports.validation`; log loss exacta; universo explícito; cobertura del 100% en la prueba interna; uniones 1:1; sin `pivot_table` | `tests/test_evaluation_v21.py`; T5 |
| 4 | Protección del holdout | Fail-closed; `verify` exige 0 accesos en estado sellado; valla de GATE 3 con autorización ligada a candidatos congelados y registro de intentos (motor y universo de evaluación) | `tests/test_gate21_protection.py`; `verify` |
| 5 | Convergencia | Verificación individual de los 226 ajustes | §4; `experiments/gate2_1/convergence_check.json` |
| 6 | Documentación | D-3 (M3 lineal frente a log1p) con sensibilidad; ubicación de `train_max_date`; registros de pytest por commit; Claude frente al auditor | §5; `reports/gate2_1/` |
| 7 | Interpretación | Conclusiones limitadas a lo evaluado; sin inferencias de rentabilidad | §6 |

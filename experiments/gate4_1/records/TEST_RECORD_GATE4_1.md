# TEST_RECORD_GATE4_1 — Ejecuciones de Claude en GATE 4.1

Todas son de Claude, en el contenedor del proyecto. **No se atribuyen al auditor independiente**, cuyo `pytest`
completo sigue sin certificarse por la falta de PyArrow en su entorno.

| # | Qué | Commit | Resultado |
|---|---|---|---|
| T1 | `tests/test_final_test.py` y `tests/test_protocol_freeze.py` con el código nuevo y el congelamiento ANTIGUO | árbol de trabajo | 21 superadas; **3 fallos esperados**: las pruebas de integridad del congelamiento detectan que el código cambió respecto de `fd8685f1…` |
| T2 | `run_final.py verify` con el congelamiento nuevo | árbol de trabajo | Código `20071ecc…`; M4-cal; entradas completas; dataset de desarrollo = autorizado |
| T3 | Ensayo con datos reales **de desarrollo** (sin holdout): réplica de identidad | árbol de trabajo | M2 y M4-cal: 61.370 de 61.370 filas iguales bit a bit; 0 accesos |
| T4 | `pytest` completo | árbol de trabajo (antes del commit) | 216 superadas, 0 fallos |
| T5 | `pytest` formal | ver `pytest_<commit>.*` | — |
| T6 | ZIP ligero en entorno virtual limpio | ver más abajo | — |

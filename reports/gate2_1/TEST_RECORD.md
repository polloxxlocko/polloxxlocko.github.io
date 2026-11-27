# TEST_RECORD — Qué ejecutó Claude y qué comprobó el auditor (GATE 2.1)

## A. Ejecutado por Claude (contenedor cloud del proyecto, Python 3.13, Linux)

Cada ejecución indica el commit exacto. "Árbol limpio" = `git status --porcelain` vacío al empezar.

| # | Qué | Commit | Resultado | Registro |
|---|---|---|---|---|
| A1 | `python -m pytest` (registro formal con JUnit) | ver `pytest_<commit>.json` | ver archivo | `reports/gate2_1/pytest_<commit>.{txt,xml,json}` (generado por `experiments/gate2_1/record_pytest.py`, que exige árbol limpio) |
| A2 | `python -m pytest` antes de cada commit de código de GATE 2.1 | `7af9669`, `a6c8745` | 157 y 158 superadas, 0 fallos (salida en el historial de la sesión; el registro formal es A1) | — |
| A3 | `python -m qsports verify` | todos los commits de GATE 2.1 | `ok: true`; accesos registrados 0/0; valla sin cruces | salida de `verify` (JSON) |
| A4 | Reproducción limpia completa (`run.py all --clean`) + `m3_spec_sensitivity` | `a6c8745` (árbol limpio) | ver `REPRODUCIBILITY_REPORT.md` | `experiments/gate2_1/repro_run/RUN_MANIFEST.json` |
| A5 | Comparación con lo publicado | — | ver `REPRODUCIBILITY_REPORT.md` | `experiments/gate2_1/repro_comparison.json` |
| A6 | Verificación de los 226 ajustes no convergentes | `a6c8745` (código del modelo) | ver `GATE_2_1_REPORT.md` §4 | `experiments/gate2_1/convergence_check.{json,_fits.csv}` |
| A7 | Evidencia sintética del evaluador | — | ver `AUDIT_RESPONSE_GATE2.md` §2 | `experiments/gate2_1/evaluator_evidence.json` |
| A8 | ZIP ligero en entorno virtual limpio (instalado con `requirements-lock.txt`) | ver `GATE_2_1_REPORT.md` §7 | pytest y `audit-synthetic` | `GATE_2_1_REPORT.md` §7 |
| A9 | Comprobación de cobertura y duplicados en las predicciones publicadas de GATE 2 | `1780027` (datos publicados) | 61.137/61.137 filas elegibles cubiertas por los 8 pronósticos; 0 duplicados (configuración, bloque, partido) en todos los archivos | `AUDIT_RESPONSE_GATE2.md` §3 |

## B. Comprobaciones del auditor independiente

El informe de auditoría recibido (GATE 2.1) contiene conclusiones y solicitudes, pero **no detalla
qué pruebas ejecutó el auditor, en qué commit ni con qué resultado**. Este registro no le atribuye
ninguna ejecución. Si el auditor aporta sus registros, se añadirán aquí, separados de los de Claude.

## C. Registro histórico de GATE 2

`reports/gate2_pytest_result.txt` ("114 passed") no indica commit y no corresponde al commit
publicado `1780027`, que tenía 115 pruebas. Se conserva con una nota de cabecera y queda sustituido
por A1.

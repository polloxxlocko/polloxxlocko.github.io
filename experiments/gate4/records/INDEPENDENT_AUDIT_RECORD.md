# INDEPENDENT_AUDIT_RECORD — Comprobaciones del auditor independiente frente a ejecuciones de Claude

## A. Auditor independiente (ChatGPT), sobre el ZIP ligero del commit `25944d9`
Fuente: mensaje del usuario del 2026-11-28. **Claude no reprodujo estas comprobaciones y no las atribuye a
sus propias ejecuciones.**

| Comprobación del auditor | Resultado informado |
|---|---|
| Hashes del paquete (`PACKAGE_MANIFEST.json`) | 414 de 414 verificados |
| `pytest` | 141 superadas, 16 omitidas (sin datos), 8 fallos y 13 errores de preparación, atribuidos a la ausencia de PyArrow en el entorno del auditor |
| `audit-synthetic` | `ok = true`, con las tres comprobaciones metodológicas superadas |
| Hash del código congelado de GATE 3 | verificado |
| Hash de resultados y autorización de GATE 3 | verificados |
| Seis categorías estadísticas almacenadas | consistentes con el evaluador |
| Registros de accesos de holdout y reserva | vacíos |
| Registro de la valla | cuatro cruces autorizados |

**Sobre PyArrow (análisis de Claude, no del auditor):** `pyarrow==19.0.1` figura en
`requirements-lock.txt`, y `pyarrow>=15` en las dependencias de `pyproject.toml`. Los fallos son
coherentes con un entorno instalado sin el archivo de bloqueo. No puedo verificar el entorno del auditor.
Desde GATE 4, `tests/conftest.py` detiene `pytest` con un mensaje explícito si falta PyArrow, en lugar de
producir fallos dispersos.

## B. Claude (contenedor del proyecto), para comparar
| Ejecución | Commit | Resultado |
|---|---|---|
| `pytest` formal (GATE 3) | `a27897a` | 178 superadas, 0 fallos (`experiments/gate3/records/pytest_a27897a.*`) |
| ZIP ligero de GATE 3 en entorno virtual limpio | `25944d9` | 162 superadas, 16 omitidas; `audit-synthetic` ok |
| `pytest` formal (GATE 4) | ver `experiments/gate4/records/TEST_RECORD_GATE4.md` | — |

Las 178 pruebas de `a27897a` y las 162 del ZIP son ejecuciones de Claude, **no** del auditor. La diferencia
de 141 frente a 162 superadas en el mismo ZIP corresponde a los 21 casos (8 + 13) que el auditor atribuye a
PyArrow.

## C. Auditor independiente (ChatGPT), revisión de GATE 4
Fuente: mensaje del usuario del 2026-11-28. **Claude no reprodujo estas comprobaciones.**

| Comprobación del auditor | Resultado informado |
|---|---|
| Hashes del paquete de GATE 4 | 433/433 |
| Archivos congelados | 39/39 |
| Hash completo del protocolo (`fd8685f1…`) | verificado |
| Pruebas automatizadas seleccionadas por no requerir PyArrow | 30 superadas, 0 fallos |
| `audit-synthetic` | satisfactorio |
| Cálculos de potencia | verificados |
| Registros de acceso de holdout y reserva | vacíos |
| `pytest` completo | **no certificado de forma independiente** (sin PyArrow en el entorno del auditor) |
| Hallazgos confirmados con pruebas sintéticas | A: el hash del holdout no se comparaba con la especificación congelada. B: una interrupción tras la carga y antes del sello permitía un segundo intento |

Corrección en GATE 4.1: ver `MODEL_AUDIT_REPORT.md` §12 y `experiments/gate4_1/`.

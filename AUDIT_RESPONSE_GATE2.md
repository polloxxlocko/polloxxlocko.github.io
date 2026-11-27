# AUDIT_RESPONSE_GATE2 — Respuesta a la auditoría independiente de GATE 2

Fecha: 2026-11-27 · Commit auditado: `1780027b` (rama `gate2`) · Correcciones: rama `gate2.1`
(código en `7af9669`, `a6c8745` y `a724e84`; la reproducción limpia corrió sobre `a724e84`; resultados
y documentos en commits posteriores que no modifican código de `src/`, `run.py` ni `configs/`).

Veredicto recibido: **aprobación metodológica condicionada**. D-1 aceptada; D-2 aceptada
condicionalmente; GATE 3 **no** autorizado; fase correctiva GATE 2.1 solicitada.

Regla que seguí: aceptar un hallazgo solo si el código, una prueba o un cálculo lo confirman, y
discrepar con evidencia si no. **Los nueve bloques de hallazgos se confirmaron en el código o en los
documentos.** No encontré ninguno incorrecto. Añado matices con evidencia y un hallazgo propio (§10).

Cifras de esta respuesta: `GATE_2_1_REPORT.md`, `REPRODUCIBILITY_REPORT.md` y los archivos que se
citan. "Ejecutado por Claude" significa ejecutado en el contenedor del proyecto. No tengo evidencia de
qué pruebas ejecutó el auditor (ver `reports/gate2_1/TEST_RECORD.md`).

---

## 1. Reproducibilidad real — ACEPTADO

**Qué estaba mal (confirmado en `src/qsports/gate2.py` de `1780027`):**
- `run_config` y `run_configs_parallel` daban una configuración por terminada si existía **alguna**
  fila suya en el archivo de predicciones. Una ejecución interrumpida entre escrituras habría dejado
  predicciones parciales tratadas como completas.
- `_append` concatenaba sobre el archivo existente. Si una configuración se volvía a calcular,
  podían quedar filas duplicadas.
- `feature_frame` reutilizaba `data/features/dev/team_ewm_hl*.parquet` con solo comprobar la
  alineación de `match_id`. No verificaba el código, los parámetros ni el contenido de los datos, y
  la caché se compartía entre ejecuciones.
- No había un modo que ignorase todo lo almacenado ni un manifiesto de hashes por ejecución.

**Corrección:**
- `gate2.configure(out, mode)`: cada ejecución usa un directorio propio. `experiments/gate2/` (lo
  publicado) es de solo lectura (`ReadOnlyError`).
- `--clean` exige un directorio nuevo o vacío y un árbol de git limpio. No lee ninguna predicción,
  variable ni resultado previo; las variables EWMA se recalculan dentro del directorio.
- Manifiesto de completitud por (configuración, bloque) y por variable. Clave de caché = SHA-256 del
  código + parámetros + temporadas + contenido exacto de las columnas de entrada. Se guarda además el
  SHA-256 del archivo y de su registro de ajustes. Sin manifiesto válido, la salida se recalcula.
- Escrituras atómicas (temporal + `os.replace`); un archivo por (configuración, bloque); nunca se
  concatena.
- `RUN_MANIFEST.json` por ejecución: commit, árbol limpio, hash de cada archivo de código y de
  configuración, hash de contenido del dataset de desarrollo, versiones, hilos BLAS, estado del sello
  y de la valla antes y después, y SHA-256 de cada artefacto.
- `experiments/gate2_1/compare_repro.py` compara la ejecución limpia con lo publicado, fila a fila.

**Evidencia:** `tests/test_gate2_cache.py` (8 pruebas: solo lectura, directorio vacío, reutilización
solo con manifiesto, archivos alterados o entradas distintas se recalculan, caché de variables
aislada y validada, duplicados, enlace de `train_max_date`, y el modo limpio reutiliza solo lo que
produjo la propia ejecución).

**Resultado de la ejecución limpia** (`REPRODUCIBILITY_REPORT.md`; commit `a724e84`, 2.400 s):
- mismas selecciones, la misma ruta de extensión D-1 y las mismas 13 categorías de la prueba interna;
- 6.474.400 de 6.485.374 predicciones (99,83%) idénticas bit a bit;
- las diferencias, < 10⁻⁸, son todas de una configuración no seleccionada (§10.4);
- la configuración `M2__h240_r16_pp`, presente en lo publicado, procedía de la ejecución detenida
  antes de D-1. Confirma que lo publicado mezclaba salidas de dos ejecuciones.

## 2. Evaluador estadístico — ACEPTADO (desviación D-4)

**Qué estaba mal:** el protocolo (§4) dice "bloques móviles de 4 semanas **calendario**
consecutivas". `_weekly_totals` agrupaba solo las semanas **con partidos**: un bloque de "4 semanas"
podía unir el final de mayo con el inicio de agosto. Confirmado en `evaluation.py` de `1780027`.

**Corrección:**
- `week_ids` devuelve un índice de semana calendario en el que semanas consecutivas tienen índices
  consecutivos.
- La serie semanal incluye explícitamente las semanas vacías (Σd = 0, n = 0), y los bloques son
  semanas de calendario (`week_mode="calendar"`, el método principal). Si una réplica queda sin
  observaciones, la evaluación falla.
- Diebold-Mariano usa la misma serie (rezagos en semanas de calendario).
- El método de semanas activas se conserva solo para comparar con lo publicado.
- Sensibilidad: bloques de 2, 4, 8 y 12 semanas con ambas definiciones, más la autocorrelación
  semanal de Δ, sobre resultados de desarrollo.
- Potencia: `power_profile` separa la superioridad (MDE frente a 0 y frente a δ) de la equivalencia
  (probabilidad de que el IC quede dentro de (−δ, δ); se necesario).

**Evidencia:**
- `tests/test_evaluation_v21.py`: semanas consecutivas, semanas vacías incluidas, réplicas vacías
  rechazadas, dependencia serial sintética, tamaño del DM, control sin dependencia, probabilidades de
  categoría frente a Monte Carlo, perfil de potencia y autocorrelación.
- `experiments/gate2_1/evaluator_evidence.json`: coberturas medidas. Con un shock semanal AR(1)
  (φ = 0,7), el IC al 95% cubre el 60% con bloques de 1 semana, el 82% con 4, el 86% con 8 y el 87%
  con 12. El DM sin HAC rechaza H0 cierta el 40% de las veces, y con HAC el 14%. Con semanas
  independientes, 91-95%.
- Conclusión honesta de esa evidencia: **si la dependencia real fuese tan persistente, el bloque
  de 4 semanas sería anticonservador.** Por eso el informe muestra la autocorrelación semanal real y
  la sensibilidad a 2-12 semanas (`GATE_2_1_REPORT.md` §3).

## 3. Validación de entradas — ACEPTADO

**Qué estaba mal:**
- `log_loss` recortaba p a [10⁻¹², 1 − 10⁻¹²] en silencio, así que p = 1,2 se habría evaluado
  como 1 − 10⁻¹².
- Faltaban comprobaciones de dimensiones, resultados binarios, faltantes y unicidad.
- `select_best` usaba `pivot_table`, que promedia duplicados en silencio.
- `paired` y `evaluate` descartaban NaN con `dropna()` sin informarlo.

**Corrección:**
- `qsports.validation`: probabilidades finitas en [0, 1], resultados 0/1, dimensiones, fechas,
  `match_id` únicos, uniones `merge_one_to_one` con `validate="one_to_one"` y cobertura frente al
  universo esperado.
- La log loss es exacta; una pérdida infinita se rechaza.
- Universo explícito por comparación. En la prueba interna se exige cobertura del 100% (una
  predicción faltante es un error). En la selección rige la muestra común preregistrada, con las
  exclusiones contadas.
- `pivot_table` sustituido por `pivot`, que falla ante duplicados, más una comprobación previa
  (también en `stability.py`).
- Política documentada en `EXPERIMENTAL_PROTOCOL.md` §4.1.

**Evidencia:**
- `tests/test_evaluation_v21.py` (rango, ±inf, NaN, no binarios, dimensiones, pérdida infinita,
  duplicados, unión 1:1, cobertura) y `evaluator_evidence.json → validation_rejections`.
- Comprobación sobre lo publicado, ejecutada por Claude: en la prueba interna las 8 predicciones
  usadas cubren el 100% de las 61.137 filas elegibles, sin `match_id` duplicados. En todos los
  archivos publicados hay 0 duplicados (configuración, bloque, partido). **El riesgo era real en el
  código, pero no alteró las cifras publicadas.**

## 4. Protección del holdout — ACEPTADO

**Qué estaba mal:**
- `reserved_ids()` ignoraba un registro faltante (`except: pass`), es decir, fallaba abierto.
- `verify` informaba los accesos registrados pero no exigía que fueran cero.
- La valla de GATE 3 se podía saltar con un booleano (`allow_beyond_fence=True`) y no registraba
  intentos.

**Corrección:**
- Fail-closed: con datos reales hacen falta los dos registros, y deben ser consistentes; solo los
  datos sintéticos (`match_id` con prefijo `syn`) se verifican sin registro.
- `verify` exige que `ACCESS_LOG.jsonl` exista y tenga 0 entradas en cada partición sellada.
- La valla exige `GATE3_AUTHORIZATION.json` ligado al SHA-256 de
  `configs/gate3_frozen_candidates.json` (no se creó ninguno de los dos) y registra todo intento en
  `logs/GATE3_FENCE_LOG.jsonl`.
- La valla también se comprueba al definir el universo de cualquier evaluación, no solo en el motor.
- Documentado: "0 accesos registrados" no es una demostración absoluta de ausencia de exposición
  (`HOLDOUT_PROTECTION_PROTOCOL.md` §3, controles 10-12, y §5).

**Evidencia:**
- `tests/test_gate21_protection.py` (9 pruebas) y `tests/test_walkforward.py` (valla).
- `python -m qsports verify` → `holdout_seal_access_log_consistent`,
  `reserve_seal_access_log_consistent` y `gate3_fence_no_unauthorized_crossing`, todas `true`;
  `access_log_entries` = 0/0.
- `RUN_MANIFEST.json → sealed_before / sealed_after` idénticos en la ejecución limpia.

## 5. Convergencia — ACEPTADO

**Qué estaba mal:** en GATE 2 afirmé que los 226 ajustes "sin convergencia" eran falsos negativos
del criterio de parada, pero solo había reajustado **24**.

**Corrección:** `experiments/gate2_1/convergence_check.py` verifica individualmente los 226:
1. Reproduce la cadena publicada de cada (configuración, bloque, división).
2. Comprueba que las predicciones coinciden bit a bit y que los mismos ajustes salen no convergentes.
3. Pule cada solución con pasos de Newton hasta max|∇f| ≤ 10⁻¹⁰·Σw (100 veces más estricto).
4. Informa la diferencia de objetivo, el gradiente residual, max|Δθ|, |Δp| máximo y medio, el
   impacto en log loss y los casos no reproducibles.

**Resultado** (`GATE_2_1_REPORT.md` §4; `experiments/gate2_1/convergence_check.json` y `_fits.csv`):
- Los 226 alcanzan el criterio estricto (gradiente final ≤ 2,1·10⁻¹³).
- f(θ publicado) − f(θ pulido) está entre −6,8·10⁻¹³ y 0, es decir, no hay mejora del objetivo a
  precisión de máquina; max|Δθ| = 7,7·10⁻⁸.
- En las 1.800 filas que predijeron, |Δp| es como máximo 2,7·10⁻⁸ (medio 4,2·10⁻⁹). El impacto
  máximo en la log loss media de una configuración es 4,5·10⁻¹².
- 223 se reproducen como no convergentes. Los 3 restantes pertenecen a la configuración no
  seleccionada `M2__h480_r64_pp`, cuyo resultado depende del orden de un `set`, y este a su vez de
  `PYTHONHASHSEED` (hallazgo nuevo de GATE 2.1, `REPRODUCIBILITY_REPORT.md` §3.2). Ningún caso quedó
  sin explicar.

## 6. Consistencia documental — ACEPTADO (desviación D-3)

- **M3 y log(1 + partidos previos):** el preregistro (A3) lo especifica, pero el código usó el
  **conteo lineal** estandarizado. Es una discrepancia, no una decisión. Queda registrada como D-3.
  Los resultados de GATE 2 corresponden a la forma lineal. Se añadió la forma preregistrada
  (`feature_columns(..., n_prior="log1p")`) y se repitió la grilla final de M3 **solo en el bloque de
  ajuste** (la prueba interna no se reevalúa), para ver si cambian la selección de M3 y la decisión
  H1b (`GATE_2_1_REPORT.md` §5). M3 no es candidato congelado.
- **`train_max_date`:** la documentación decía que estaba en cada predicción. En realidad está en
  los fitlogs, un registro por ajuste, enlazable por (`config_id`, `block`, `scope`, `fit_tau`).
  Corregido en `AUDIT_RUN.md`, `MODEL_SPECIFICATION.md` (A7, A8) y en el docstring del motor.
  Prueba: `test_train_max_date_stored_per_fit_and_joinable`.
- **Registros de pytest:** `reports/gate2_pytest_result.txt` decía "114 passed" sin commit; el
  commit publicado `1780027` tenía 115 pruebas. Nuevo registro con commit exacto, árbol limpio,
  entorno, JUnit y conteos (`experiments/gate2_1/record_pytest.py` → `reports/gate2_1/pytest_<commit>.*`).
  El archivo antiguo se conserva como histórico, marcado como sin commit.
- **Claude frente al auditor:** `reports/gate2_1/TEST_RECORD.md` separa lo que ejecutó Claude
  (con commit y salida) de lo que comprobó el auditor (no documentado en el informe recibido).

## 7. Interpretación científica — ACEPTADO

Sustituí las afirmaciones generales en `GATE_2_REPORT.md` (§1, §5.5, §7.3), `README.md`,
`CLAUDE.md`, `MODEL_SPECIFICATION.md` (B2), `EXPERIMENTAL_PROTOCOL.md` §6 y `LIMITATIONS.md`.

Nueva formulación: "**en 2014/15-2021/22, con M4-sport definido por la desviación logit p_M2* −
logit p_A y comparado con M4-cal, no se demostró aporte incremental (EQ)**". No afirma nada sobre
otras variables, formulaciones, modelos o períodos.

Eliminada la frase "la expectativa económica es negativa tras el margen". La equivalencia
predictiva no demuestra una rentabilidad negativa ni una positiva; Q3 se evalúa aparte
(`EXPERIMENTAL_PROTOCOL.md` §6).

## 8. Restricciones — CUMPLIDAS

No se modificaron los candidatos congelados (M4-sport h730 r1000 con X = desviación de M2*, M4-cal
h730, M2*), ni el mercado, ni las fuentes. No se implementó M5. No se evaluó 2022/23-2023/24: el
registro de la valla no tiene ningún intento. No se abrieron el holdout ni la reserva: 0 accesos
registrados. No se fusionó con `main`. Solo se leyó el conteo de **nivel 0** del holdout (metadatos
permitidos) para la potencia, como en GATE 2.

## 9. Entregables

| Entregable | Ubicación |
|---|---|
| Respuesta a la auditoría | este documento |
| Informe de GATE 2.1 | `GATE_2_1_REPORT.md` |
| Informe de reproducibilidad | `REPRODUCIBILITY_REPORT.md` |
| Registro de pruebas | `reports/gate2_1/pytest_<commit>.{txt,xml,json}`, `reports/gate2_1/TEST_RECORD.md` |
| Manifiesto de hashes | `reports/gate2_1/HASH_MANIFEST.json`; por ejecución, `experiments/gate2_1/repro_run/RUN_MANIFEST.json` |
| Evidencia de cada corrección | pruebas citadas arriba; `experiments/gate2_1/*.json` |
| Comparación original frente a reproducido | `experiments/gate2_1/repro_comparison.json`, resumida en `REPRODUCIBILITY_REPORT.md` |
| ZIP ligero | `python -m qsports audit-package --light` → `dist/audit_package_gate2_1_light.zip` (sin Parquet) |

## 10. Matices (sin discrepar del hallazgo)

1. **Semanas activas frente a calendario.** Las dos variantes son estimadores defendibles bajo
   dependencia de corto alcance. El problema real era que el código no hacía lo que el protocolo
   decía. Corregí el código para cumplir el protocolo, no al revés, y muestro ambas.
2. **Riesgos de código frente a efecto en las cifras.** Las cachés y las uniones permisivas eran
   riesgos reales. La reproducción limpia y las comprobaciones de cobertura y duplicados miden si
   alguno se materializó en lo publicado (`REPRODUCIBILITY_REPORT.md`).
3. **La evidencia sintética también me corrige.** La prueba de dependencia serial muestra que
   ningún bloque de 2-12 semanas da cobertura nominal con dependencia muy persistente. No lo oculto:
   lo uso para leer la sensibilidad real (§2). En los datos de desarrollo la autocorrelación semanal
   es baja y ninguna categoría cambia con el bloque.
4. **Hallazgo propio de GATE 2.1 (no señalado por el auditor).** La reproducción limpia descubrió un
   no determinismo en el prior de ascendidos de M2: el orden de iteración de un `set` depende de
   `PYTHONHASHSEED`. Afecta solo a configuraciones `_pp` no seleccionadas, con diferencias < 10⁻⁸. Lo
   documento y propongo una corrección de una línea, sin aplicarla: cambiaría el código después de la
   reproducción oficial (`REPRODUCIBILITY_REPORT.md` §3.2).

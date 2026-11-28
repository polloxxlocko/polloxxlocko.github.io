# EXPERIMENT_LOG — Registro de experimentos

Registro **append-only**. Cada entrada incluye fecha, objetivo, datos y versión, código,
resultado (incluidos los negativos) y qué conjuntos de datos se examinaron. Nunca se
borran entradas. Las correcciones se registran como entradas nuevas.

---

## E-000 · 2026-11-27 · Fase Cero: auditorías y selección de mercado

**Tipo:** auditoría descriptiva (sin modelos, sin backtests, sin estrategias).

**Código y salidas**
| Script | Salida |
|---|---|
| `phase0/download_football_data.py` | `data/raw/football_data/<temporada>/data.zip` + `manifest.jsonl` (SHA-256) |
| `phase0/audit_football_data.py` | `reports/phase0/football_data_*.csv`, `football_data_audit_summary.json`, `pinnacle_vs_b365_ou_fairprob_absdiff.csv` |
| `phase0/verify_references.py` | `research/references_verified.json` (resúmenes solo locales, ver E-002) |
| `phase0/market_selection.py` (semilla 20261127) | `reports/phase0/market_selection_results.json`, `market_selection_tables.md` |

**Datos:** Football-Data.co.uk, temporadas 2000/01-2026/27, descargadas el 2026-11-27
(27 archivos, 17 MB). Versión identificada por los SHA-256 del manifiesto.

**Datos examinados (transparencia sobre el conjunto de prueba):**
- Cobertura, márgenes y comparación Pinnacle-Bet365: **todas** las temporadas. Solo usan
  cuotas y presencia de datos, no resultados.
- Estadísticas que dependen del resultado (tasa de Over 2,5, varianza/media de goles,
  Brier del mercado): **solo temporadas ≤ 2023/24**. Los resultados de 2024/25 en adelante
  **no se examinaron**.
- *Revelación:* el Brier del mercado de cierre se calculó para 2019/20-2023/24, que incluye
  el período de validación propuesto (2022/23-2023/24). Es una medida del benchmark, no de
  un modelo, y no ajusta ningún parámetro. Se registra por transparencia.

**Resultados principales**
1. 200.825 partidos; 0 duplicados reales; 0 incoherencias `FTR`; 10 cuotas < 1,01.
2. Cuotas O/U 2,5: pre-cierre desde 2005/06 (~100%); pre-cierre y cierre multi-casa desde
   2019/20 (~100%); Pinnacle cae al 38% (2025/26) y al 0% (2026/27).
3. Pinnacle de cierre post-23/07/2025: la discrepancia con Bet365 se duplica (media
   0,0060 → 0,0127; p90 0,0126 → 0,0304). Confirma empíricamente la advertencia de la fuente.
4. Sin cuotas de córners ni tarjetas. Árbitro solo en Inglaterra y Escocia. xG solo en 2026/27.
5. Brier de cierre O/U (2019/20-2023/24): 0,2406 frente a 0,25 de la climatología dentro de
   muestra.
6. Matriz de selección: empate exacto O/U 2,5 = 1X2 = 4,55. NBA ganador tercero (3,05).
   Córners y tarjetas no elegibles.
7. Criterios secundarios: O/U con 99,5% de precios ≤ 3,50 (1X2: 66,6%) y desviación del
   retorno 0,97 (1X2: 1,24).

**Problemas encontrados y correcciones (resultados negativos del proceso)**
- **5 de 56 DOIs escritos de memoria eran incorrectos:** hubacek2019, dixon_pope2004,
  gandar1998_nba, manner2016_nba, dawson2007. Resolvían a artículos de otros temas o daban
  404. Se corrigieron con búsqueda en Crossref y se re-verificaron. **Lección:** nunca
  citar sin verificar el DOI.
- En el primer análisis, el parser descartaba 6.302 filas con más campos que la cabecera
  y detectaba 755 "duplicados" falsos (alias `HT/AT`). Se corrigió el parser, que ahora
  recupera 8.038 filas y da 0 duplicados.
- Una afirmación preliminar (Paul y Weinbach 2002 como evidencia NBA) se corrigió tras
  leer el resumen: trata de totales **NFL**.
- El subagente que intentó leer Wheatcroft (2020) no pudo extraer el texto del PDF. Se
  extrajo localmente con `pdftotext` y se leyó.

**Decisiones abiertas:** ver `MARKET_SELECTION_REPORT.md` §9.

---

## E-001 · 2026-11-27 · GATE 1: infraestructura de datos y protección del holdout

**Tipo:** infraestructura y auditoría (sin modelos, sin evaluación de modelos, sin acceso
al holdout).
**Autorización:** GATE 0 aprobado por el usuario (mercado O/U 2,5 prepartido, 22
divisiones, holdout 2024/25-2025/26).

**Acciones (en orden):**
1. **Separación física inmediata** de 2024/25-2025/26 (`data/holdout/raw/`) y 2026/27
   (`data/prospective/raw/`), antes de cualquier otro trabajo. Hashes verificados contra
   el manifiesto original.
2. Paquete `qsports` (ingesta, temporalidad, holdout, benchmarks, calidad, verificación,
   CLI) y configuraciones (`holdout`, `source_reliability`, `exclusion_criteria`,
   `team_aliases`).
3. Sellado: registros de match_ids, metadatos de nivel 0 y hashes. Dataset de desarrollo
   con guarda anti-reservados.
4. Benchmarks A/A′/A*/B/C para desarrollo; inventario, calidad, exclusiones y diagnósticos
   temporales y de Pinnacle.
5. 59 pruebas automáticas (todas pasan); pruebas de mutación del tripwire y de la
   verificación de hashes (ambas detectaron la alteración).
6. Reconstrucción desde cero en un clon limpio + venv nuevo + descarga nueva: hashes RAW y
   de contenido idénticos.

**Decisiones metodológicas:**
- 2026/27 sellada como reserva prospectiva (conservador; pendiente de confirmar por el usuario).
- Benchmark A = promedio pre-cierre de la fuente (proporcional). B = cierre, solo
  retrospectivo. C = frecuencia histórica point-in-time.
- Corte de información: resultados con fecha estrictamente anterior a la captura estimada.
- Regla PIN-2025-07-23: enmascarar todas las cuotas de Pinnacle desde esa fecha, sin
  eliminar partidos.
- Validez de un par: cuotas ≥ 1,01 y margen en [0; 0,25]. Sin combinar casas.
- 5 alias de equipos (1 empírico, 4 por juicio); `match_id` con nombres crudos.
- Criterios de exclusión objetivos predefinidos: ninguna división excluida.

**Resultados verificables:** desarrollo 182.821 filas (182.818 en el universo de
entrenamiento); muestra primaria A 146.350; holdout 15.328 filas y prospectivo 2.680
(nivel 0); `verify` 10/10; pytest 59/59.

**Problemas encontrados (todos resueltos o registrados):**
- `git mv -k` no movió los archivos no versionados en la primera separación física: se
  detectó al listar y se corrigió con `mv` antes de seguir.
- pandas 3: `astype(str)` no convierte nulos → claves duplicadas por `match_id`.
- Fila artefacto `#REF!` (T1 2013/14); 2 partidos griegos sin resultado.
- Variante de nombre "Raith"/"Raith Rvs" (misma temporada) no detectada por la primera
  prueba de colisiones: se añadió una búsqueda de prefijos/subcadenas.
- Invariante temporal falso por una fila sin fecha: la comprobación ahora excluye filas
  sin fecha y las reporta.
- Hash de contenido distinto entre reconstrucciones por la marca de descarga: se excluyen
  las columnas de procedencia temporal (registradas aparte).
- `process.py` leía manifiestos reservados (solo fechas y hashes): se movió a `holdout.py`
  para cumplir el tripwire.

**Exposición del holdout:** ver `HOLDOUT_PROTECTION_PROTOCOL.md` §5. Ningún resultado
reservado observado. Las cifras de desarrollo usadas para la potencia (σ_Δ sustituto =
0,114, de LL_C − LL_A en 2005/06-2021/22) **no** usan la validación ni el holdout.

---

## E-002 · 2026-11-27 · Publicación para auditoría independiente

**Solicitud del usuario:** publicar el proyecto en `polloxxlocko/polloxxlocko.github.io`,
eliminando los archivos previos y conservando el historial, para una auditoría externa.

**Acciones:**
1. Escaneo de secretos y datos personales en los 76 archivos versionados y en todo el
   historial: sin hallazgos.
2. **Exclusión de resúmenes de artículos en texto plano** (OpenAlex no los redistribuye por
   razones legales): reescritura del historial limitada a `research/` (banderas
   `abstract_available_*`). Commits antiguos purgados. Respaldo local no publicado.
3. `verify_references.py`: resúmenes solo locales (gitignored); el paso de Semantic Scholar
   (antes un comando suelto) queda como código reproducible.
4. Descargador de la Fase Cero: por defecto solo temporadas de desarrollo (≤ 2023/24).
5. **Verificación de reproducibilidad en un clon limpio** (venv nuevo + descarga nueva):
   - Fase Cero: estadísticas de resultados, sensibilidad y filas de desarrollo idénticas.
     Las cifras que incluían temporadas hoy selladas no son reproducibles por diseño; su
     versión solo con desarrollo lleva a la misma conclusión (AUDIT_GUIDE §5).
   - GATE 1: 7/7 hashes de contenido idénticos, informes idénticos, verify ok, 59/59 pruebas.
6. `AUDIT_GUIDE.md` para auditores.

**Resultado negativo / defecto encontrado:** `verify_references.py` no reintentaba ante
HTTP 429 y sobrescribía el archivo verificado con 8 referencias vacías. Corregido
(reintentos con espera exponencial; sin sobrescritura si algo falla). Tras la corrección:
59/59 DOIs idénticos. En `research/references_verified.json`, la bandera de Semantic
Scholar pasa a `null` en los 38 DOIs no consultados en la Fase Cero (antes `False`).

**Holdout:** sin accesos (ACCESS_LOG vacío). Solo se publican registros (ids hash, conteos,
hashes), sin cuotas ni resultados.

---

## E-003 · 2026-11-27 · GATE 2: preregistro, evaluador, walk-forward y modelos (infraestructura)

**Autorización:** GATE 2 aprobado por el usuario con 10 exigencias adicionales. GATE 3 no
autorizado.

**Antes de cualquier experimento:**
1. Partición `prospective` renombrada a `reserve` (reserva histórica sellada), para no
   confundirla con validación prospectiva genuina (exigencia 2). Código, configuración,
   pruebas y directorios actualizados; `verify` ok; 59/59 pruebas.
2. EXPERIMENTAL_PROTOCOL §6 reescrito con 6 categorías mutuamente excluyentes (S-R, S-NR,
   EQ, INC, I-NR, I-R) y §10 (reserva frente a prospectiva genuina) (exigencias 1 y 2).
3. Preregistro `MODEL_SPECIFICATION.md` §A + `configs/gate2.json`, commit `e35e224`
   (2026-11-27T02:42Z), antes de escribir modelos.

**Infraestructura (exigencia 3: evaluador y walk-forward antes que los modelos):**
- `evaluation.py` (23 pruebas: calibración, Murphy, ECE, AUC, cobertura del bootstrap
  por bloques, DM, partición de decisión verificada con predicados independientes).
- `walkforward.py` (valla ≤ 2021/22; lista blanca de columnas pre-partido; aserción de
  entrenamiento < τ), `features.py` (EWMA con `merge_asof` estricto), `synthetic.py`.
- `models.py` (FreqModel, PoissonModel M1/M2, LogisticFeatureModel M3, MarketModel
  M4-cal/M4-sport, MarketNull).
- Pruebas anti-filtración en entrenamiento, features, transformaciones (independencia de
  lote), calibración y selección (invariancia al futuro en todos los modelos).

**Problemas encontrados y resolución (resultados negativos del proceso):**
- La primera prueba de invariancia de M3 falló. Diagnóstico: error de **la prueba**, no
  del modelo. Con reajuste cada 4 capturas, un ajuste en τ_k ≤ τ0 predice capturas
  posteriores a τ0 cuyas variables usan legítimamente datos anteriores a su propia captura.
  La propiedad correcta se define por fecha de captura del partido. Corregida.
- Validación metodológica sintética de M4 (antes de usar datos reales): con mercado
  completo, M4-sport − M4-cal = INC (+0,0006); con mercado que ignora la forma, S-R
  (−0,0060). Convertida en prueba automática.
- `forkserver` no admite `lambda` ni scripts por stdin → fábricas con `functools.partial`
  y ejecución desde script.
- **Optimizador:** L-BFGS-B tardaba ~59 ms por ajuste Poisson (95% en la rutina interna
  de SciPy). Se sustituyó por **Newton-Raphson con Hessiana analítica** y búsqueda lineal
  de Armijo: 7,8 ms por ajuste, mediana de 3 iteraciones, óptimo igual o mejor (prueba
  `test_poisson_hessian_matches_numerical_and_newton_matches_lbfgs`). **Desviación de la
  Parte A** (que decía "L-BFGS"): no cambia el modelo ni el óptimo, solo el algoritmo.
- **Sobresuscripción de hilos BLAS:** la primera ejecución real (4 procesos × varios hilos
  sobre 4 núcleos) tardó 243 s por configuración. Con 1 hilo por proceso: 22 s. Se detuvo
  la ejecución y sus salidas se **conservan** en
  `experiments/gate2/aborted_run1_blas_multithread/`. Diferencia máxima de probabilidad
  entre ambas ejecuciones: 6,7·10⁻⁹ (equivalentes). Una ejecución anterior con L-BFGS se
  detuvo antes de producir predicciones.
- `rm` de la copia de trabajo antigua (`/home/user/quantitative-sports`) denegado por el
  sistema de permisos. La copia sigue en el disco, sin archivos RAW (movidos al
  repositorio actual).

**Desviación D-1 (2026-11-27, antes de ver M3, M4 o la prueba interna).** La selección
Poisson en el bloque de ajuste quedó en el **borde** de la grilla preregistrada (M1: ridge
16 y ventana 1.095 días, ambos máximos; M2: ridge 16, máximo). Una grilla que no acota el
óptimo produce una evaluación sesgada. Se detuvo la cadena **antes** de la prueba interna
y se fijó una regla uniforme (`configs/gate2.json → boundary_rule`): extender hacia
afuera cualquier dimensión numérica con ≥ 3 valores cuyo óptimo quede en el borde (×1,5
ventanas; ×2 ridge y semivida Poisson; ×10 ridge logística), con un máximo de 3 pasos y solo
con el bloque de ajuste. En ese momento había 9 configuraciones M3 guardadas cuyas métricas
**no se habían consultado**. Todas las configuraciones (originales y extendidas) se
conservan.

---

## E-004 · 2026-11-27 · GATE 2: resultados de ajuste, prueba interna y diagnósticos

**Ejecución:** `python experiments/gate2/run.py all` (1.343 s) tras D-1. Todas las salidas en
`experiments/gate2/` (91 configuraciones, ~6,6 M de predicciones fuera de muestra, ~474.500
ajustes registrados). Una primera ejecución "all" se detuvo **antes** de la prueba interna
para aplicar D-1. Su registro se conserva en `log_all_run1_stopped_D1.txt`; las 9
configuraciones M3 que había calculado se reutilizaron sin consultarse antes de fijar D-1.

**Bloque de ajuste (decisiones de la escalera):**
- M1* = ventana 1.095 d, ridge 128 (en el borde tras 3 extensiones: limitación).
  M2* = semivida 480 d, ridge 64 (interior). Prior de ascendidos: no mejora → no adoptado.
- M2 frente a M1: −0,00057 [−0,00080; −0,00035] S-NR → M2 justificado.
- H1b (tiros frente a goles en M3): −0,00003 [−0,00024; +0,00018] EQ → **resultado negativo**
  para H1b con este diseño. Los tiros no entran en M4-sport.
- M5: dispersión 1,017 [1,005; 1,030]; r residual 0,0135 [0,0055; 0,0216] → ninguna extensión
  justificada. **No se implementó M5.**
- M4-cal* = semivida 730 d; M4-sport* = semivida 730 d, ridge 1.000 (interior tras 1
  extensión).

**Prueba interna 2014/15-2021/22 (n = 61.137; una evaluación por familia):**
M2 − A = +0,00480 (I-R); M4-cal − A = −0,00008 (EQ); **M4-sport − M4-cal = −0,00001
[−0,00006; +0,00004] (EQ)**; M2 − C = −0,00593 (S-R); M3 − M2 = +0,00075 (I-NR).
Coherente por temporada y por régimen. Tabla completa en `MODEL_SPECIFICATION.md` §B2.

**Convergencia:** M1 63/216.819 y M2 163/234.249 ajustes marcados sin convergencia
(gradiente ≤ 2·10⁻⁵). Reajuste de alta precisión de 24 casos: |Δp| máx = 2,1·10⁻⁹ →
falsos negativos del criterio de parada (mejora recomendada: criterio por decremento de
Newton). M3 y M4: 0 sin convergencia.

**Predicciones NaN (registradas, excluidas por muestra común):** M1 264 y M2 286 (primeros
partidos de divisiones sin historia previa, p. ej. EC 2005/06); M4-cal 421 y M4-sport 735
(menos de 200 filas de entrenamiento con entradas disponibles al inicio de 2006/07).

**Almacenamiento:** predicciones reorganizadas en un archivo por configuración
(`p_over` float64 idéntico bit a bit; λ en float32, error < 4,2·10⁻⁷; `train_max_date` y
`n_train` retirados de las predicciones porque están en los registros de ajuste).

**Incidencia de proceso:** el commit `7d9ee26` se hizo con 1 prueba fallida (tripwire sobre
`audit_package.py`, que nombraba rutas reservadas para excluirlas). Corregido en `ec0b3d0`
centralizando las marcas en `holdout.py`. Desde entonces los commits se condicionan al
código de salida de pytest.

## E-005 · 2026-11-27 · GATE 2.1: correcciones de la auditoría independiente de GATE 2

**Motivo:** auditoría independiente de GATE 2 sobre `1780027b`, con aprobación metodológica
condicionada (D-1 aceptada; D-2 aceptada condicionalmente; GATE 3 no autorizado). Respuesta
punto por punto en `AUDIT_RESPONSE_GATE2.md`.

**Cambios de código** (rama `gate2.1`; `7af9669`, `a6c8745`, `a724e84`):
- Ejecución reproducible: directorio propio por ejecución, `--clean`, cachés solo con
  manifiesto de completitud (clave de caché + SHA-256), escrituras atómicas, `RUN_MANIFEST.json`
  con hashes; `experiments/gate2/` en solo lectura.
- Evaluador: validación de entradas, log loss exacta (`log1p`), bootstrap por semanas
  **calendario** (D-4), sensibilidad de bloque, autocorrelación semanal, potencia de
  superioridad frente a equivalencia.
- Uniones 1:1, universo explícito y cobertura completa en la prueba interna; sin `pivot_table`.
- Holdout: registro fail-closed; `verify` exige 0 accesos en estado sellado; valla de GATE 3
  con autorización ligada a candidatos congelados y registro de intentos, comprobada también
  en el universo de evaluación.
- M3: forma `log1p` del preregistro disponible para la sensibilidad (D-3).

**Desviaciones nuevas:**
- **D-3** (detectada por la auditoría): M3 usó el conteo lineal de partidos previos, no
  log(1 + n). Los resultados de GATE 2 son los de la forma lineal. Sensibilidad con log1p solo
  en el bloque de ajuste.
- **D-4** (detectada por la auditoría): el bootstrap usó bloques de semanas activas, no de
  semanas calendario. Corregido; el método antiguo se conserva solo para comparar.

**Incidencias de proceso en GATE 2.1 (registradas por transparencia):**
- La primera ejecución limpia se detuvo sola porque el archivo de registro, creado dentro del
  repositorio, ensuciaba el árbol. Se movió fuera del repositorio.
- Se reinició una vez para añadir la valla al universo de evaluación (cambio de código, y por
  tanto de hash).
- Se reinició otra vez porque el modo limpio recalculaba, dentro de la misma ejecución, las
  configuraciones ya validadas al extender la grilla. El resultado no cambiaba, pero el tiempo de
  cálculo más que se duplicaba. Corregido en `a724e84`.
- Ninguna de las ejecuciones interrumpidas llegó a la prueba interna ni se usó para nada; sus
  directorios se borraron antes de relanzar.

**Resultados (ejecución limpia sobre `a724e84`; detalle en `GATE_2_1_REPORT.md`):**
- **Reproducción:** selecciones, ruta D-1 y las 13 categorías de la prueba interna, idénticas.
  6.474.400 de 6.485.374 predicciones (99,83%) iguales bit a bit; el resto, solo en
  `M2__h480_r64_pp`, difiere < 10⁻⁸. `M2__h240_r16_pp` (publicada) procedía de la ejecución
  detenida antes de D-1.
- **Hallazgo nuevo:** el prior de ascendidos no es determinista (orden de un `set` según
  `PYTHONHASHSEED`; comprobado con semillas 0, 1 y 2). Afecta solo a `_pp`. Corrección propuesta,
  no aplicada.
- **Evaluador corregido:** ninguna categoría cambia con semanas calendario ni con bloques de 2, 4,
  8 o 12 semanas. La autocorrelación semanal de Δ está entre −0,07 y +0,19 (rezagos 1, 2 y 4).
  M4-sport − M4-cal = −0,00001 [−0,00006; +0,00004] EQ.
- **Potencia (holdout, N = 15.154):** las comparaciones de M4 pueden demostrar equivalencia si
  |θ| < ~6-9·10⁻⁴. Para declarar S-R, la mejora real tendría que ser > ~1,1·10⁻³. M2 − A no puede
  demostrar equivalencia.
- **Convergencia:** 226/226 verificados. Criterio estricto alcanzado en todos; |Δp| ≤ 2,7·10⁻⁸;
  impacto ≤ 4,5·10⁻¹² en la log loss media; 3 casos no reproducidos, todos de `_pp`.
- **D-3:** con log1p, la misma selección de M3 y la misma decisión H1b (EQ). La prueba interna no
  se reevaluó.

## E-006 · 2026-11-27 · GATE 3: validación 2022/23-2023/24 (una sola evaluación)

**Autorización:** el usuario aprobó el cierre de GATE 2.1, aceptó definitivamente D-1 a D-4 y autorizó
GATE 3 tras cinco comprobaciones previas. Las cinco se cumplieron:
- corrección `sorted(departed)` (`ea5598d`);
- prueba con varios `PYTHONHASHSEED`, que falla con el código antiguo;
- nueva reproducción limpia, con los candidatos idénticos bit a bit y mismo SHA-256;
- ejecutor con verificación de identidad e hiperparámetros y réplica de identidad en la prueba interna;
- congelamiento (`e339fc6`) y autorización ligada a su hash (`3bf3750`).

Preregistro en `MODEL_SPECIFICATION.md` Parte C (`e2ac6da`), comprometido antes de evaluar.

**Ejecución:** `python experiments/gate3/run_gate3.py run --out experiments/gate3/validation_run`
(árbol limpio en `3bf3750`; una vez; sello `logs/GATE3_EVALUATED.json`).

**Resultados** (n = 15.488; bloques de 4 semanas calendario; δ = 0,001):
- **M4-sport − M4-cal = −0,000007 [−0,000129; +0,000111] EQ** (comparación principal).
- M4-sport − A = −0,00042 [−0,00077; −0,00008] S-NR.
- M4-cal − A = −0,00042 [−0,00075; −0,00008] S-NR.
- M2 − A = +0,00635 I-R; M2 − C = −0,00835 S-R; A − C = −0,0147 S-R.

Las categorías no cambian con bloques de 2-12 semanas. La pendiente de calibración de A es 1,20; la de
M4-cal, 1,06. El AUC de A y de M4 es igual (0,6097-0,6098). Q2, condición 1: dirección negativa
(consistente). Q3 no evaluada.

**Lectura:** el aporte deportivo de la desviación de M2 sigue sin demostrarse. La pequeña mejora sobre A
procede de recalibrar el consenso. **VENTAJA ESTADÍSTICA NO DEMOSTRADA** (relevante).

## E-007 · 2026-11-28 · GATE 4: auditoría de M4-cal y congelamiento de la prueba final

**Decisiones del usuario:**
- GATE 3 aprobado.
- Candidato primario único: **M4-cal h730**, con la configuración exacta evaluada.
- Q3 queda NO EVALUADA en el experimento confirmatorio.
- GATE 4 autorizado; apertura del holdout **no** autorizada.
- La auditoría independiente ejecutó el ZIP de `25944d9`
  (`experiments/gate4/records/INDEPENDENT_AUDIT_RECORD.md`).

**Trabajo:**
1. Auditoría de M4-cal: `tests/test_m4cal_audit.py` (8 pruebas) y `experiments/gate4/m4cal_audit.py`.
2. Modo autorizado del holdout en el motor y el universo, con la reserva siempre prohibida
   (`tests/test_gate4_holdout_mode.py`).
3. Ejecutor de la prueba final `qsports.final_test`, probado solo con datos sintéticos
   (`tests/test_final_test.py`). Se ensayó con datos reales **de desarrollo** (identidad bit a bit, hashes
   del dataset), sin el holdout.
4. Ajuste no convergente de GATE 3 documentado sin repetir la evaluación (solo datos anteriores a τ).
5. Potencia reestimada con GATE 3.
6. Congelamiento (`configs/final_test_frozen.json`, `PROTOCOL_FREEZE.json`).

**Hallazgos de la auditoría:**
- El argumento ridge de M4-cal es inerte.
- La máscara de `inp_m2` excluye 10 de 146.585 filas utilizables; M2* se ejecuta como auxiliar en el
  holdout para reproducirla.
- El recorte de p_A no actúa.
- 0 de 385 ajustes no convergentes, con b ∈ [1,004; 1,234].
- El ajuste no convergente de GATE 3 (F2, 2022-07-29) se reproduce exactamente y su pulido cambia p en
  ≤ 2,3·10⁻⁸; no afecta a M4-cal.

**Potencia con GATE 3:** se en el holdout de 1,75·10⁻⁴. Para S-R hace falta una mejora real de
≥ 1,49·10⁻³. Si la diferencia real fuese la de GATE 3: P(S-NR) = 0,67 y P(EQ) = 0,33.

## E-008 · 2026-11-28 · GATE 4.1: controles de ejecución de la prueba final

**Motivo:** la auditoría independiente de GATE 4 fue favorable respecto de M4-cal y del protocolo
estadístico. Verificó 433/433 hashes, 39/39 archivos congelados, el hash del protocolo, 30 pruebas sin PyArrow,
`audit-synthetic` y la potencia. Confirmó dos hallazgos con pruebas sintéticas:
- **A:** el hash del holdout no se comparaba con la especificación congelada.
- **B:** una interrupción entre la carga y el sello permitía un segundo intento.

**Corrección (solo `src/qsports/final_test.py`):**
- A: triple coincidencia (registro, especificación y datos), con comprobación previa del registro frente a
  la especificación antes de abrir.
- B: marcador exclusivo y persistente justo antes de abrir, más el registro de estados `started`, `opened`,
  `finished` e `interrupted`.
- Pruebas: 8 sintéticas nuevas en `tests/test_final_test.py` (interrupción, segundo intento, concurrencia,
  fallos previos que no consumen el intento, y la triple coincidencia) y una manipulación más en la
  verificación de la especificación.

**Alcance demostrado:**
- de los 39 archivos congelados cambian 3 (ejecutor, protocolo v1.1, especificación);
- en la especificación solo cambian `code_hash` y la fecha;
- la réplica de identidad de desarrollo sigue siendo bit a bit;
- no se repitieron los experimentos de desarrollo.

**Nuevo congelamiento:** hash del protocolo `9c81e30189ba6732106873810f75140e79b71a3ac2152589d8f65421c601e63f`.
El holdout **no** se abrió.

## E-009 · 2026-11-28 · Prueba final: evaluación única del holdout 2024/25-2025/26

**Autorización:** expresa del usuario, ligada al protocolo `9c81e301…` (`HOLDOUT_AUTHORIZATION.json`,
commit `bb2f3d6`). Comprobaciones previas superadas: hash del protocolo, integridad de RAW y nivel 0, sin
duplicados, 0 accesos, identidad y dataset de desarrollo.

**Ejecución:** `python experiments/final/run_final.py run --out experiments/final/holdout_run`, una vez,
02:49:58-02:50:59 UTC. Estados `started`, `opened` y `finished`. Holdout cargado `b859bdab…` = registro =
especificación.

**Resultados** (n = 15.154; cobertura 100%):
- Q1: M4-cal − C = −0,013835 [−0,016962; −0,011030] **S-R → AFIRMATIVO**.
- Q2: M4-cal − A = +0,000057 [−0,000292; +0,000381] **EQ → VENTAJA ESTADÍSTICA NO DEMOSTRADA**. Las tres
  condiciones de validez se cumplen; pendiente de M4-cal 0,922 y de A 1,039.
- Q3: NO EVALUADA.
- Categorías estables con bloques de 2 a 12 semanas y por temporada.

**Incidente I-1:** a las 02:53:00, durante `pytest`, una prueba antigua dependiente del estado abrió el
holdout real (entrada `"test"` en el registro de accesos). Fue posterior al sello y sin cálculos.
Documentado y corregido solo en las pruebas (guarda en conftest; pruebas herméticas). El registro se
conserva intacto.

**Archivos congelados:** sin cambios; el hash sigue siendo `9c81e301…`. Reserva: 0 accesos. Informe
definitivo: `FINAL_EXPERIMENT_REPORT.md`.

## E-010 · 2026-11-28 · Cierre de la primera línea de investigación

**Decisión del usuario:**
- cierre del experimento confirmatorio aprobado;
- veredictos aceptados: Q1 AFIRMATIVO, Q2 VENTAJA ESTADÍSTICA NO DEMOSTRADA, Q3 NO EVALUADA;
- incidente I-1 aceptado como incidencia de procedimiento posterior al sellado que no invalida los
  resultados.

**Auditoría independiente del cierre** (ChatGPT, según el usuario):
- 449/449 hashes del paquete;
- 39/39 archivos congelados sin cambios desde GATE 4.1;
- hash del protocolo y hash de resultados coincidentes con el sello;
- 35 pruebas superadas, 0 fallos, 1 omitida y 4 excluidas;
- `pytest` completo sin certificar (sin PyArrow).

**Reglas a partir de ahora:**
- conservar todo;
- no reevaluar el holdout;
- reserva sellada;
- sin modelos nuevos ni Q3;
- no fusionar con `main`;
- nuevas investigaciones solo con hipótesis nueva, evidencia y autorización expresa.

La primera línea queda **oficialmente concluida**.

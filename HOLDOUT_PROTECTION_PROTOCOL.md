# HOLDOUT_PROTECTION_PROTOCOL — Protección del conjunto de prueba final

Versión 1.0 · 2026-11-27 · GATE 1

## 1. Particiones (configs/holdout.json)

| Partición | Temporadas | Partidos (filas) | Estado | Uso permitido |
|---|---|---:|---|---|
| **dev** | 2000/01–2023/24 | 182.821 | Abierta | Todo el desarrollo: variables, modelos, hiperparámetros, calibración, umbrales, estrategias, exploración |
| **holdout** | 2024/25, 2025/26 | 15.328 | **SELLADA** | Solo metadatos de nivel 0 (§2) hasta la autorización del usuario |
| **reserve** (antes `prospective`) | 2026/27 en adelante | 2.680 (descargadas el 2026-11-27) | **SELLADA** | Solo nivel 0. **Reserva histórica**, no validación prospectiva (§7) |

**Decisión conservadora de GATE 1 sobre 2026/27.** El usuario reservó 2024/25 y 2025/26.
La temporada 2026/27 es *posterior* al holdout. Usarla en desarrollo dejaría que información
futura respecto del conjunto de prueba influyera en el diseño del modelo. Por eso se sella
también, como **reserva histórica sellada** (confirmado por el usuario al aprobar GATE 1). En GATE 2 la
partición se renombró de `prospective` a `reserve` para no confundirla con una validación
prospectiva genuina (§7).

## 2. Niveles de acceso a datos reservados

| Nivel | Contenido | Acceso |
|---|---|---|
| **0 — Metadatos** | `match_id`, división, temporada, fecha, hora, equipos, regla de captura y banderas booleanas de presencia/validez de campos (p. ej. `has_ou_pre_avg_pair`, `has_result`, `ou_pre_avg_overround_in_range`) | Permitido sin autorización (inventario e integridad) |
| **1 — Valores de cuotas** | Precios, probabilidades implícitas, márgenes | **Prohibido** sin autorización |
| **2 — Resultados** | Goles, resultado, estadísticas del partido (tiros, córners, tarjetas, árbitro, xG) | **Prohibido** sin autorización |

Justificación del nivel 0: el inventario y la auditoría de integridad necesitan saber
*si* un campo existe. Una bandera booleana de presencia o validez (p. ej. "el par promedio
tiene margen en [0; 0,25]") no informa sobre resultados ni permite ajustar nada.

## 3. Mecanismos implementados

| # | Control | Implementación | Prueba automática |
|---|---|---|---|
| 1 | **Separación física** | RAW reservado en `data/holdout/raw/` y `data/reserve/raw/`; procesados reservados en `data/{holdout,reserve}/processed/`. Desarrollo solo en `data/raw/` y `data/processed/dev/` | `test_dev_only_contains_dev_seasons`; `verify`: `no_reserved_seasons_in_raw_dev` |
| 2 | **Descarga enrutada** | `qsports.ingest.download_seasons` escribe cada temporada en el RAW de su partición. El descargador histórico de la Fase Cero se niega a descargar temporadas ≥ 2024/25 | — |
| 3 | **Registro de match_ids reservados** | `data/{holdout,reserve}/registry.json`: ids, conteos y hashes, sin resultados ni cuotas | `test_assert_no_reserved_rejects_reserved_match_ids_even_if_relabelled` |
| 4 | **Guarda en tiempo de ejecución** | `holdout.assert_no_reserved(df)` rechaza temporadas reservadas **o** ids registrados, aunque la temporada se haya re-etiquetado. Se llama en `load_dev()`, `load_dev_benchmarks()` y la construcción. **Todo pipeline de GATE 2+ debe cargar datos solo con `process.load_dev()`** | `test_assert_no_reserved_rejects_reserved_seasons`; `test_dev_and_reserved_ids_disjoint` |
| 5 | **Autorización ligada al protocolo** | `holdout.open_reserved()` exige `HOLDOUT_AUTHORIZATION.json` con firmante, fecha, declaración, propósito y el **hash del protocolo congelado** (`PROTOCOL_FREEZE.json`). Si cualquier archivo congelado cambia, el acceso se deniega | `test_open_reserved_denied_in_current_project_state`; `test_authorization_flow_hash_binding_and_access_log`; `test_incomplete_authorization_rejected` |
| 6 | **Registro de accesos append-only** | Cada apertura añade una línea a `data/{holdout,reserve}/ACCESS_LOG.jsonl` (versionado en git) | `test_authorization_flow_hash_binding_and_access_log`; `verify`: `access_log_entries = 0` |
| 7 | **Tripwire de código** | Ningún archivo `.py` fuera de `paths.py`, `holdout.py` y `test_holdout.py` puede contener rutas o funciones de acceso reservado; los notebooks tampoco | `test_tripwire_reserved_paths`; `test_tripwire_notebooks_do_not_read_reserved` |
| 8 | **Nivel 0 sin valores** | Los metadatos reservados no contienen columnas de goles, estadísticas ni cuotas | `test_level0_contains_no_values` |
| 9 | **Hashes de integridad** | SHA-256 de cada `data.zip` reservado y hash de contenido del nivel 0, en el registro. `python -m qsports verify` los recalcula | `test_verify_all_ok` |
| 10 | **Registro fail-closed** (GATE 2.1) | Con datos reales, `assert_no_reserved` exige los registros de partidos reservados de ambas particiones; si falta uno o es inconsistente (`n_matches` ≠ número de ids), lanza `ReservedDataError` en lugar de asumir que no hay reservados. Solo los datos sintéticos (todos los `match_id` con prefijo `syn`) se verifican sin registro | `test_missing_registry_fails_closed_for_real_data`; `test_inconsistent_registry_fails_closed`; `test_walkforward_refuses_real_data_without_registry` |
| 11 | **Sello con cero accesos** (GATE 2.1) | `verify` exige, para cada partición sin archivo de autorización, que `ACCESS_LOG.jsonl` **exista** y tenga **0** entradas (`*_seal_access_log_consistent`). Si hay autorización, cada acceso debe corresponder a su hash de protocolo | `test_sealed_state_requires_existing_empty_access_log`; `test_current_project_is_sealed_with_zero_accesses` |
| 12 | **Valla de GATE 3 con autorización y registro** (GATE 2.1) | Evaluar temporadas posteriores a 2021/22 exige `GATE3_AUTHORIZATION.json` (firmante, fecha, declaración del usuario, propósito) ligado al SHA-256 de `configs/gate3_frozen_candidates.json`. Ya no existe un interruptor booleano. **Todo intento**, permitido o rechazado, se anota en `logs/GATE3_FENCE_LOG.jsonl`; `verify` falla si hay un cruce permitido sin autorización vigente | `test_fence_blocks_validation_block_and_logs_attempt`; `test_gate3_authorization_binding_and_logging`; `test_incomplete_gate3_authorization_refused`; `test_real_fence_log_has_no_crossings` |

**Pruebas de mutación hechas en GATE 1** (para confirmar que los controles detectan
fallos reales):
- Se añadió un script que lee `data/holdout/...` → el tripwire **falló** como debía.
- Se alteró un byte del `data.zip` de 2026/27 → `verify` **marcó** la alteración (`*_raw_unchanged = false`).

Ambas mutaciones se revirtieron y el hash original se comprobó.

**Cero accesos registrados no es ausencia demostrada de exposición (GATE 2.1).** El registro
de accesos prueba que no se usó la función de apertura autorizada. No prueba por sí solo que
nadie haya visto datos reservados por otras vías: la exposición previa de nivel 1 de la Fase
Cero (§5), las cifras agregadas que circularon antes del sellado, una lectura deliberada de
los Parquet fuera del código o lo que haya visto cualquier persona que haya tenido acceso a
la fuente pública. Por eso los informes dicen "0 accesos registrados", no "sin exposición".

**Alcance honesto de la protección:** los controles impiden el uso **accidental**. No
impiden que alguien con acceso al sistema de archivos lea los Parquet a propósito. La
protección contra el uso deliberado es de procedimiento: CLAUDE.md prohíbe a cualquier
agente crear el archivo de autorización sin una instrucción expresa del usuario, y todo
acceso legítimo queda en el registro.

## 4. Hashes de integridad (estado sellado, 2026-11-27)

| Archivo | SHA-256 |
|---|---|
| `data/holdout/raw/football_data/2425/data.zip` | `4dc3abfdc48a6b7e507873f356e9ef84c24e86e6dd654995a050e1aa5ed9f0de` |
| `data/holdout/raw/football_data/2526/data.zip` | `0cf572edf7185ac08bb56b0940056ed693a6300d7ca348c91700bbd5f9bbfa66` |
| `data/reserve/raw/football_data/2627/data.zip` | `91f57d2f687f87781d3d07347eea2b8acedbf51f74e8ced2f84d52df50b11cdf` |

Coinciden con los hashes de la descarga original de la Fase Cero (manifiesto RAW), así que
los archivos no cambiaron entre la descarga y el sellado. Los hashes de contenido de los
procesados están en `data/processed/MANIFEST.json` y en cada `registry.json`.

## 5. Registro de exposición previa (Fase Cero y GATE 1)

### 5.1 Qué se tocó del período reservado durante la Fase Cero (2026-11-27, antes del sellado)

| Uso | Nivel | Detalle | ¿Se observaron resultados? |
|---|---|---|---|
| Conteo de partidos y cobertura de columnas | 0 | Presencia de cuotas y estadísticas por temporada | No |
| Medianas de overround por división-temporada (desde 2019/20) | **1** | Incluyó 2024/25-2026/27 en agregados ("O/U Bet365 5,9%") | No |
| Diferencia Pinnacle-Bet365 antes/después del 23/07/2025 | **1** | Probabilidades justas de Over de ambas casas (agregados) | No |
| Criterios secundarios O/U vs 1X2 (precios ≤ 3,50, desviación del retorno, margen) | **1** | Cuotas de cierre Bet365 de 2019/20 a 2026/27 | No |
| Comprobación de coherencia `FTR` vs goles | **2 (procesado)** | El script recorrió los marcadores de todas las temporadas y solo informó un conteo de incoherencias (0). No se calculó ni mostró ninguna estadística de resultados | **No se observaron**; el código sí los procesó |
| Tasa de Over 2,5, varianza/media de goles, Brier del mercado | 2 | **Restringido a ≤ 2023/24 desde el diseño** | No |

Los archivos `reports/phase0/football_data_coverage_by_season_div.csv` y
`pinnacle_vs_b365_ou_fairprob_absdiff.csv` contienen agregados de nivel 1 de temporadas
reservadas. Se conservan como registro histórico y **no deben usarse en ninguna decisión
de modelado**.

### 5.2 Qué se tocó durante GATE 1
- El sellado leyó el RAW reservado (todas las columnas) para escribir el Parquet completo
  sellado y los metadatos de nivel 0. No se calculó ninguna estadística de cuotas ni de
  resultados.
- Se mostraron metadatos de nivel 0: conteos, presencia mensual de Pinnacle, Bet365 y
  promedio, una fila sin resultado (Bastia-Red Star, F2, 05/12/2025) y nombres de equipos.
- Los nombres de equipos de nivel 0 de temporadas reservadas se usaron para detectar
  variantes de nombre. Una decisión de alias ("Boston" → "Boston Utd") afecta a filas de
  2024/25+.

### 5.3 Evaluación de consecuencias metodológicas
1. **No se observó ningún resultado del período reservado.** Por eso no hay contaminación
   directa de las métricas predictivas (tasas de Over, pérdidas de modelos o del mercado).
2. **La elección del mercado (O/U frente a 1X2) no dependió de cuotas reservadas.**
   Recalculados solo con desarrollo (2019/20-2023/24), los criterios dan lo mismo: precios
   ≤ 3,50 = 99,45% frente a 66,7%; desviación del retorno = 0,974 frente a 1,240.
3. **La regla de exclusión de Pinnacle** se basa en la declaración publicada por la fuente.
   La verificación empírica con cuotas reservadas solo la corroboró. Además, la presencia de
   nivel 0 muestra que Pinnacle **no existe** en el dataset desde febrero de 2026, así que
   no podría ser benchmark del holdout en ningún caso. La decisión no depende del
   rendimiento ni de resultados.
4. **Los agregados de margen** de temporadas reservadas no revelan resultados y no se
   usaron para fijar umbrales. El rango de validez [0; 0,25] es una regla de validez de
   datos.
5. **Riesgo residual: bajo.** No hay acción correctiva necesaria más allá de este registro
   y de la prohibición de reutilizar los agregados de la Fase Cero.

## 6. Procedimiento para abrir el holdout (solo tras GATE 4)

1. Completar GATE 2-4 solo con desarrollo.
2. Congelar el protocolo: crear `PROTOCOL_FREEZE.json` con la lista de archivos que
   definen el experimento (EXPERIMENTAL_PROTOCOL.md, MARKET_BENCHMARK_SPECIFICATION.md,
   configs, código del modelo final y la versión de los parámetros). Commit en git.
3. Presentar al usuario el protocolo congelado y su hash.
4. **Solo con la autorización expresa del usuario** en la conversación, crear
   `HOLDOUT_AUTHORIZATION.json` con: `partition`, `authorized_by`, `authorized_at`,
   `user_statement` (cita textual), `purpose` y `protocol_freeze_sha256`.
5. Ejecutar **una única** evaluación preregistrada. El acceso queda en `ACCESS_LOG.jsonl`.
   Desde GATE 4: `python experiments/final/run_final.py run --out DIR` (`qsports.final_test`). El
   ejecutor hace, en este orden:
   - verifica la autorización y la identidad del candidato, del código y de las entradas;
   - comprueba el hash del dataset de desarrollo;
   - hace la réplica de identidad;
   - comprueba que el hash del registro del holdout es igual al de la especificación congelada (GATE 4.1);
   - crea el marcador exclusivo y persistente `logs/FINAL_TEST_ATTEMPT.json` (GATE 4.1);
   - carga el holdout con `holdout.load_authorized_holdout`, lo que deja una entrada en el registro de
     accesos;
   - verifica que su hash de contenido coincide con el registro **y** con la especificación;
   - evalúa una sola vez y escribe el sello `logs/FINAL_TEST_EVALUATED.json`.

   Los estados (`started`, `opened`, `finished`, `interrupted`) quedan en `logs/FINAL_TEST_STATE_LOG.jsonl`.
   Con el marcador presente, no hay reintentos automáticos.

   El motor y el universo solo admiten filas del holdout con esa autorización, verificada de nuevo en
   cada llamada, y cada uso queda registrado como `allowed-holdout` en `logs/GATE3_FENCE_LOG.jsonl`. La
   reserva sigue prohibida.
6. Una vez abierto, el holdout deja de ser independiente: ningún ajuste posterior puede
   evaluarse en él.

## 7. Reserva histórica sellada frente a validación prospectiva genuina

La reserva 2026/27 **no** es una validación prospectiva. Sus partidos ya se disputaron y sus
resultados se descargaron el 2026-11-27, antes de registrar ninguna predicción. Su
protección es procedimental. Una validación prospectiva genuina (GATE 5) exige predicciones
registradas y publicadas **antes** de cada partido, con testigo temporal externo (commit y
push). Ver `EXPERIMENTAL_PROTOCOL.md` §10. Ningún resultado de la reserva se presentará como
prospectivo.


## 8. Estado tras la prueba final (2026-11-28)
- **Holdout 2024/25-2025/26:** abierto una vez, con la autorización expresa del usuario ligada al protocolo
  `9c81e301…`. La evaluación única quedó sellada a las 02:50:59 UTC. Ya **no** es independiente.
- **Registro de accesos del holdout: 2 entradas.**
  - (1) La evaluación preregistrada, a las 02:50:46.
  - (2) **Incidente I-1**, a las 02:53:00: una prueba automática antigua, dependiente del estado, abrió el
    holdout durante `pytest`, ya con la autorización vigente. Datos cargados y descartados; sin cálculos;
    posterior al sello. La entrada se conserva sin alterar. Corrección: guarda en `tests/conftest.py` que
    impide a cualquier prueba abrir datos reservados reales.
- **Reserva 2026/27:** sellada, 0 accesos.

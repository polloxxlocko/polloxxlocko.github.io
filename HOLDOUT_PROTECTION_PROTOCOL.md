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

**Pruebas de mutación hechas en GATE 1** (para confirmar que los controles detectan
fallos reales):
- Se añadió un script que lee `data/holdout/...` → el tripwire **falló** como debía.
- Se alteró un byte del `data.zip` de 2026/27 → `verify` **marcó** la alteración (`*_raw_unchanged = false`).

Ambas mutaciones se revirtieron y el hash original se comprobó.

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
6. Una vez abierto, el holdout deja de ser independiente: ningún ajuste posterior puede
   evaluarse en él.

## 7. Reserva histórica sellada frente a validación prospectiva genuina

La reserva 2026/27 **no** es una validación prospectiva. Sus partidos ya se disputaron y sus
resultados se descargaron el 2026-11-27, antes de registrar ninguna predicción. Su
protección es procedimental. Una validación prospectiva genuina (GATE 5) exige predicciones
registradas y publicadas **antes** de cada partido, con testigo temporal externo (commit y
push). Ver `EXPERIMENTAL_PROTOCOL.md` §10. Ningún resultado de la reserva se presentará como
prospectivo.


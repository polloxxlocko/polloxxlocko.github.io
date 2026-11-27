# DATA_QUALITY_REPORT — Calidad e integridad de los datos

Versión 1.0 · 2026-11-27 · GATE 1 · Fuente de las cifras: `reports/gate1/quality_dev.json`,
`exclusions.json`, `benchmark_coverage.json` (generados por `python -m qsports reports`)

Las comprobaciones **que dependen de valores** se hicieron **solo con desarrollo**
(2000/01-2023/24). En las particiones selladas solo se comprobó lo que permite el nivel 0
(conteos, fechas, duplicados de clave, presencia y validez booleana).

## 1. Resumen

| Prueba | Resultado (desarrollo) | Tratamiento |
|---|---|---|
| Filas parseadas | 182.821 (22 divisiones, 24 temporadas) | — |
| Filas descartadas por el parser | **0** | Se recuperan las filas anchas |
| Filas con más campos que la cabecera | 8.038 en 2001/02-2009/10 | Recuperadas con cabecera extendida (alineación probada) |
| Codificación | utf-8-sig: 176.676 filas; cp1252: 6.145 (15 archivos antiguos) | Detección automática por archivo |
| Cabeceras con nombres repetidos | 1 archivo (2004/05 D2: `LB`) | Desambiguadas con sufijo |
| Fechas no parseables | 1 (artefacto `#REF!`, T1 2013/14) | Excluida |
| Fechas fuera de la ventana de temporada | 0 | — |
| Claves duplicadas (div, fecha, local, visitante) | 0 | — |
| Partidos sin resultado | 2 (G1 2014/15, G1 2018/19) | Excluidos del entrenamiento |
| `FTR` incoherente con el marcador | 0 | — |
| Goles del descanso > goles finales | 0 | — |
| `HTR` incoherente con el descanso | 1 (EC 2007/08 Oxford-Ebbsfleet) | Bandera `flag_htr_inconsistent` (HTR no se usa) |
| Goles fuera de [0; 15] o no enteros | 0 | — |
| Tiros a puerta > tiros | 16 filas (11 en 2000/01) | Bandera `flag_shots_target_gt_shots`; relevante para M3 |
| Rojas > 5 | 1 (SP2 2020/21 Zaragoza-Oviedo, 9 rojas visitantes) | Bandera `flag_red_cards_gt_5`; error evidente |
| Valores no numéricos en columnas numéricas | `#REF!` (T1 2013/14), `#` (N1 2022/23, cierre 1X2 B365), `NA` (asistencia, E2 2000/01) | Convertidos a nulo y registrados |
| Cuotas < 1,01 | O/U cierre: B365 1+1, promedio 1; 1X2 B365: 10 | Inválidas para benchmarks |

Ningún valor crudo se modifica: las anomalías se marcan con banderas por fila y los
originales se conservan en RAW (inmutable, con SHA-256).

## 2. Márgenes de los pares O/U 2,5 (desarrollo)

| Par | n | Mediana | p1 | p99 | < 0 | > 0,25 |
|---|---:|---:|---:|---:|---:|---:|
| Promedio pre (A) | 146.635 | 6,60% | 4,47% | 10,19% | 18 | 31 |
| — Betbrain (2005/06-2018/19) | 108.680 | 6,90% | | | | |
| — Oddsportal (2019/20-2023/24) | 37.955 | 5,87% | | | | |
| Bet365 pre | 42.670 | 5,88% | 2,59% | 8,19% | 12 | 0 |
| Pinnacle pre | 37.737 | 3,58% | 2,36% | 6,50% | 0 | 0 |
| Gamebookers pre (2002-2005) | 17.047 | 9,92% | 7,53% | 12,14% | 11 | 2 |
| Promedio cierre (B) | 37.971 | 5,82% | 4,32% | 7,49% | 0 | 0 |
| Bet365 cierre | 37.937 | 5,81% | 2,59% | 7,03% | 0 | 0 |
| Pinnacle cierre | 37.889 | 3,44% | 2,32% | 5,52% | 0 | 1 |
| Máximo pre (combina casas) | 146.635 | 1,72% | −1,07% | 6,04% | **7.469** | 6 |
| Máximo cierre (combina casas) | 37.972 | 0,95% | −3,81% | 3,87% | **10.036** | 0 |

Consecuencias:
1. 49 pares A inválidos por margen fuera de rango (18 negativos, 31 > 25%) más 256 sin par:
   305 partidos ≥ 2005/06 sin benchmark A.
2. El "margen" negativo frecuente del par de máximos confirma que combinar casas no
   produce probabilidades justas (ver MARKET_BENCHMARK_SPECIFICATION.md §1).

## 3. Identidad de equipos

| Prueba | Resultado |
|---|---|
| Equipos por división-temporada | Mínimo 10 (SC1 2000/01), máximo 24 (E1 2000/01), coherente con los formatos de liga |
| Equipo-temporadas con < 10 apariciones | 1: "Raith" en SC1 2004/05 (1 partido) |
| Colisiones por mayúsculas o puntuación | 0 |
| Nombres no ASCII | 1: "King’s Lynn" (apóstrofo tipográfico), sin variante ASCII |
| Mismo nombre en dos países | 0 |
| Búsqueda de prefijos/subcadenas dentro de cada país (incluye nombres de nivel 0 reservados) | 25 candidatos revisados; **5 alias aplicados**, 20 clubes distintos (`configs/team_aliases.json`) |

Alias aplicados (el nombre crudo se conserva en `home_team_raw`/`away_team_raw`; el
`match_id` usa el nombre crudo):

| País | Crudo | Canónico | Evidencia | Filas dev |
|---|---|---|---|---:|
| Escocia | Raith | Raith Rvs | **E**: misma temporada, 35 + 1 = 36 partidos | 1 |
| Grecia | OFI | OFI Crete | J: denominaciones sin solapamiento | 394 |
| Países Bajos | Roda | Roda JC | J | 238 |
| Países Bajos | Sparta | Sparta Rotterdam | J | 238 |
| Inglaterra | Boston | Boston Utd | J | 230 |

**Limitación conocida:** la identidad se basa en el nombre. Los clubes refundados que
reutilizan un nombre (p. ej. "Chester": Chester City hasta 2009 y Chester FC desde 2010)
quedan fusionados. Los clubes refundados con nombre distinto (Airdrieonians/Airdrie Utd)
quedan separados. El impacto previsto es bajo y concentrado en divisiones inferiores.

## 4. Criterios de exclusión aplicados (definidos antes de modelar)

| Criterio (`configs/exclusion_criteria.json`) | Resultado |
|---|---|
| Universo de entrenamiento | 182.818 incluidos; excluidos: 2 sin resultado y 1 sin fecha |
| Comparación A (≥ 2005/06): par válido | 146.585 válidos; 256 sin par; 49 margen fuera de rango |
| Comparación A: ambigüedad de captura | 235 excluidos |
| **Muestra primaria A** | **146.350** |
| División-temporada < 80% elegible | Ninguna |
| Divisiones excluidas | **Ninguna (22/22 se mantienen)** |

Ninguna exclusión usa resultados predictivos ni económicos.

## 5. Particiones selladas (nivel 0)

| Comprobación | Holdout | Prospectivo |
|---|---|---|
| Filas | 15.328 | 2.680 |
| `match_id` únicos | Sí | Sí |
| Fechas no parseables | 0 | 0 |
| Filas sin resultado (presencia) | 1 (F2 2025/26, Bastia-Red Star) | 0 |
| Hash RAW = descarga original | Sí | Sí |
| Validez de valores (goles, cuotas) | **No evaluada**; se evaluará tras la autorización de apertura | ídem |

## 6. Reproducibilidad

`python -m qsports verify` (resultado en GATE 1: **ok**):
- Hashes RAW de desarrollo = manifiesto = descarga original de la Fase Cero.
- Hash de contenido de `matches.parquet` y `market_benchmarks.parquet` = `MANIFEST.json`.
- Ninguna temporada reservada en RAW de desarrollo; el dataset de desarrollo no contiene
  ids reservados.
- RAW y nivel 0 reservados sin cambios. Registro de accesos: 0 entradas.

# MARKET_BENCHMARK_SPECIFICATION — Benchmarks de mercado y elementales

Versión 1.0 · 2026-11-27 · GATE 1 · Implementación: `src/qsports/benchmark.py` ·
Pruebas: `tests/test_benchmark.py`, `tests/test_integration.py`

Esta especificación se fija **antes** de entrenar cualquier modelo. Cambiarla después
requiere una entrada en `EXPERIMENT_LOG.md` y, si afecta a la prueba final, autorización
del usuario.

## 1. Principios

1. **Mismo operador, mismo momento.** La probabilidad sin margen se calcula solo a partir
   de un par Over/Under de la **misma casa** (o del mismo agregado publicado por la fuente)
   y del **mismo momento** (pre-cierre o cierre).
2. **Prohibido combinar casas** para estimar márgenes o probabilidades justas. El par de
   máximos (`Max`/`BbMx`) mezcla casas distintas. Evidencia en desarrollo: su "margen" es
   **negativo** en 7.469 partidos con cuota previa (5,1%) y en 10.036 al cierre (26,4%).
   Solo se usa como "mejor precio disponible" en análisis económicos explícitamente
   rotulados.
3. **Ninguna casa es la verdad.** Bet365 es una casa individual con su propio margen y sus
   sesgos. Pinnacle se trata igual, con reglas de confiabilidad por período.
4. **Comparaciones sobre muestras idénticas.** Toda comparación entre modelo y benchmarks
   se hace sobre filas donde *todos* los elementos comparados son válidos
   (`benchmark.common_sample`).
5. **No se selecciona la referencia por rendimiento.** La jerarquía de benchmarks se fija
   aquí. Está prohibido elegir a posteriori la casa "más difícil" o "más fácil" de batir.

## 2. Método de eliminación del margen

- **Primario:** normalización proporcional, `p_over = (1/Q_over) / (1/Q_over + 1/Q_under)`.
- **Alternativo (solo sensibilidad, preregistrado):** método de potencia (Clarke et al.
  2017), `p_i = (1/Q_i)^k` con `Σ p_i = 1`. Implementado y probado en
  `odds.normalize_power`. En mercados de dos resultados, Shin equivale al método aditivo
  (Clarke et al. 2017), por lo que no se implementa por separado.

## 3. Validez de un par

| Regla | Valor | Motivo |
|---|---|---|
| Ambas cuotas presentes | — | Mercado completo |
| Cuota mínima | ≥ 1,01 | Valores < 1,01 son errores de datos (encontrados: 3 en O/U cierre de desarrollo) |
| Rango de overround | [0; 0,25] | En una sola casa o agregado no puede haber margen negativo; > 25% indica error de captura. Regla de validez de datos, no de rendimiento |
| Confiabilidad de la fuente | `configs/source_reliability.json` | Enmascara solo las cuotas afectadas; **nunca elimina el partido** |

Motivos de invalidez registrados por fila: `missing`, `odds<1.01`,
`overround_out_of_range`, `source_unreliable`.

## 4. Referencias

### A — Benchmark PRINCIPAL: mercado pre-cierre (comparable temporalmente)

- **Definición:** par **promedio de mercado pre-cierre** publicado por la fuente,
  normalizado de forma proporcional → `p_A_consensus`.
  - 2005/06-2018/19: `BbAv>2.5`/`BbAv<2.5` (promedio de Betbrain).
  - 2019/20+: `Avg>2.5`/`Avg<2.5` (promedio de Oddsportal).
- **Por qué es el principal:** es el único conjunto de cuotas pre-cierre con cobertura de
  todo el período de desarrollo con mercado (≈100% desde 2005/06). Es un consenso de
  muchas casas y corresponde al momento de captura que define el conjunto informativo del
  modelo (§`TEMPORAL_INTEGRITY_REPORT.md`).
- **Comparabilidad temporal:** el modelo solo usa resultados con fecha estrictamente
  anterior a la fecha estimada de captura de esta cuota.
- **Régimen:** el cambio Betbrain → Oddsportal (2019/20) altera la composición del
  promedio (margen mediano 6,9% frente a 5,9%). Toda evaluación se reporta también **por
  régimen**. En el período reservado, desde el 23/07/2025 el promedio deja de incluir a
  Pinnacle (marcador de régimen `AVG-NOPIN-2025-07-23`).

### A′ — Por casa, pre-cierre (secundarias)

| Casa | Columna | Cobertura en desarrollo | Margen mediano | Notas |
|---|---|---|---:|---|
| Bet365 | `p_A_b365` | 2019/20-2023/24 (~99,6%); 2002/03-2004/05 parcial (16-26%) | 5,9% | Casa individual |
| Pinnacle | `p_A_pin` | 2019/20-2023/24 (~99%) | 3,6% | **No confiable desde el 23/07/2025** |
| Gamebookers | `p_A_gb` | 2002/03-2004/05 (66-87%) | 9,9% | Antes del período de comparación |

### A* — Consenso alternativo predefinido

Media simple de las probabilidades justas de las casas individuales **válidas y
confiables** en ese partido (`p_Astar_books_mean`, `Astar_n_books`). En desarrollo,
2019/20+: 37.669 partidos con 2 casas, 269 con 1 y 66 con 0. Se usa solo como análisis de
robustez del benchmark A.

### B — Benchmark SECUNDARIO: cierre (solo retrospectivo)

- `p_B_consensus` (promedio de cierre `AvgC`), `p_B_b365`, `p_B_pin` (con la misma regla
  de Pinnacle).
- Disponible desde 2019/20. **No se usa nunca como predictor**, ni como benchmark
  principal. Sirve como referencia retrospectiva (cuánto se acercó el modelo al precio
  final) y para el cálculo del CLV.
- Margen mediano de cierre en desarrollo: promedio 5,8%, Bet365 5,8%, Pinnacle 3,4%.

### C — Benchmark ELEMENTAL: frecuencia histórica point-in-time

- `p_C_hist_freq = (k + 1) / (n + 2)`: proporción de Over 2,5 en **todos** los partidos
  previos de la **misma división** con fecha estrictamente anterior a
  `info_cutoff_date`, con ventana expansiva desde 2000/01 y prior de Laplace Beta(1,1).
- Responde a la pregunta 1 (¿supera el modelo a una referencia estadística simple?).
- Verificación: coincide con el cálculo por fuerza bruta en las muestras probadas
  (0 discrepancias en 300 + 150 partidos).

## 5. Tratamiento de Pinnacle

| Hecho | Evidencia |
|---|---|
| La fuente declara que, desde el 23/07/2025, las cuotas de Pinnacle están "systematically out of date", tanto pre-cierre como cierre, y las excluye de promedios y máximos | `data.php`, texto verificado |
| En desarrollo (2019/20-2023/24), la diferencia con Bet365 es **estable**: media \|Δp\| = 0,0062-0,0082 por temporada | `reports/gate1/pinnacle_investigation.json` |
| En la Fase Cero (nivel 1, antes del sellado), la diferencia de cierre se duplicó tras el 23/07/2025 | `HOLDOUT_PROTECTION_PROTOCOL.md` §5 |
| Presencia (nivel 0) en el período reservado: ~99% hasta sep-2025; oct 94%, nov 37%, dic 48%, ene-2026 19%; **0% desde feb-2026** | ídem |
| Presencia ≠ fiabilidad: en ago-sep 2025 Pinnacle sigue presente pero ya es no fiable según la fuente | — |
| Bet365 y el promedio siguen presentes ≈100% en todo el período reservado | Nivel 0 |

**Regla (`PIN-2025-07-23`):** desde el 23/07/2025 se enmascaran **todas** las cuotas de
Pinnacle, pre-cierre y cierre. Se toma la declaración de la fuente aunque la verificación
propia solo detectó degradación al cierre: es la opción conservadora. No se elimina ningún
partido, y los benchmarks A, A′-Bet365 y B siguen disponibles. Pinnacle se reporta como
referencia por casa **solo hasta el 22/07/2025**.

## 6. Muestras de comparación (desarrollo)

| Muestra (temporadas 2005/06-2023/24, con resultado, sin duplicados) | Partidos |
|---|---:|
| A válido | 146.585 |
| A válido y sin ambigüedad de captura (**muestra primaria de la pregunta 2**) | **146.350** |
| A + A′-Bet365 | 37.870 |
| A + A′-Bet365 + A′-Pinnacle | 37.669 |
| A + B | 37.953 |
| A + B + A′-Bet365 + B-Bet365 | 37.847 |
| C disponible | 146.890 |

Diferencia media \|p_A − p_A′-Bet365\| en 2019/20-2023/24: 0,0052.

## 7. Universo de entrenamiento frente a subconjunto de comparación

- **Universo de entrenamiento** (`configs/exclusion_criteria.json`): 182.818 partidos con
  fecha, equipos y resultado, sin claves duplicadas (2000/01-2023/24). Incluye temporadas
  sin cuotas, útiles para estimar fuerzas de equipos.
- **Subconjunto elegible para comparar con el mercado (A):** 146.350 partidos
  (2005/06-2023/24) con par A válido y sin ambigüedad de captura.
- Ninguna división-temporada queda por debajo del mínimo del 80% de elegibilidad.
  **Ninguna división se excluye.**

## 8. Uso económico (pregunta 3)

- Cuotas de ejecución simulada: **solo precios observados**, de una sola casa o agregado,
  en el momento pre-cierre (Bet365 pre o promedio pre). El "mejor precio" (máximo) se
  reporta por separado como cota superior no alcanzable para un usuario de una sola casa.
- **Coolbet: no hay cuotas históricas.** Ningún resultado económico se extrapola a Coolbet
  (limitación fundamental registrada en `LIMITATIONS.md`).

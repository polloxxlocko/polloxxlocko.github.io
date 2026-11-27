# MODEL_SPECIFICATION — Especificación y preregistro de GATE 2

Versión 1.0 (preregistro) · 2026-11-27 · Configuración: `configs/gate2.json`

Este documento se escribió y versionó **antes** de ejecutar cualquier experimento de
GATE 2. Los resultados se añaden en la Parte B sin modificar la Parte A. Cualquier
desviación de la Parte A se registra en `EXPERIMENT_LOG.md` con su motivo.

---

## Parte A — Preregistro

### A1. Alcance autorizado y límites
- Autorizado (2026-11-27): evaluador estadístico, infraestructura walk-forward y modelos
  M1-M5 **según el protocolo**, con las 10 exigencias adicionales del usuario.
- **No autorizado:** GATE 3. El bloque de validación 2022/23-2023/24 queda **vallado**:
  `walkforward.run` se niega a evaluar temporadas posteriores a 2021/22. Holdout y
  reserva siguen sellados.
- Exigencia 9: ningún modelo se implementa solo por estar en la hoja de ruta. Cada
  peldaño se construye si la regla de §A5 lo justifica con datos del bloque de ajuste.

### A2. Bloques temporales (solo desarrollo)

| Bloque | Temporadas | Uso |
|---|---|---|
| Burn-in | 2000/01-2004/05 | Solo entrenamiento |
| **Ajuste** | 2005/06-2013/14 (Poisson); 2006/07-2013/14 (modelos apilados, que necesitan predicciones fuera de muestra previas) | Grillas, selección de variables, decisiones de la escalera |
| **Prueba interna** | 2014/15-2021/22 | **Una** evaluación por familia ya ajustada |
| Validación (GATE 3) | 2022/23-2023/24 | Vallado |

Ningún entrenamiento usa partidos de 2022/23 en adelante: todas las fechas de corte de
GATE 2 son ≤ 2022-06-30.

### A3. Escalera de modelos

| Peldaño | Modelo | Especificación |
|---|---|---|
| M0a | Frecuencia histórica (C) | `(k+1)/(n+2)` por división, point-in-time (GATE 1) |
| M0b | Mercado (A = M4-null) | Consenso pre-cierre sin margen (GATE 1) |
| M1 | Poisson con ventana | Por división: `log λ_h = μ + η + att_h − def_a`, `log λ_a = μ + att_a − def_h`; pesos 1 dentro de la ventana; ridge κ/2·Σ(att² + def²); μ y η sin penalizar; L-BFGS con gradiente analítico; reajuste en cada fecha de captura |
| M2 | Poisson con decaimiento | Igual que M1 con pesos `exp(−ln2·edad/semivida)` (historia ≤ 4 años). Etapa 2: prior de equipos nuevos en la división = media de los (att, def) de los equipos que la dejaron la temporada anterior |
| M3 | Logística ridge independiente | `logit p = β0 + γ·logit(p_C) + βᵀX`; X = EWMA (semivida en partidos) por equipo de goles a favor/en contra (G), tiros (S), tiros a puerta (T) y córners (C), más indicadores de faltante y log(1 + partidos previos). Estandarización e imputación ajustadas **solo** con filas de entrenamiento |
| M4-cal | Recalibración del mercado | `logit p = a + b·logit(p_A)`; sin información deportiva |
| M4-sport | Mercado + deporte | `logit p = a + b·logit(p_A) + βᵀX_sport`; X_sport = desviaciones `logit p_M2* − logit p_A` (y `logit p_M3* − logit p_A` si M3 entra por la regla de §A5); ridge solo sobre β; mismo esquema de pesos y reajuste que M4-cal |
| M5 | Extensiones | Solo si las reglas diagnósticas de §A5 se cumplen |

**M4-cal frente a M4-sport (exigencia 4).** Ambos se ajustan con el mismo procedimiento,
las mismas filas, los mismos pesos y el mismo calendario de reajuste. La única diferencia
es el término `βᵀX_sport`. Por tanto, Δ(M4-sport − M4-cal) aísla la información deportiva
incremental, más allá de una recalibración del mercado. Se clasifica con la partición del
§6 del protocolo. Solo S-R o S-NR permiten afirmar un aporte deportivo incremental.

### A4. Selección de hiperparámetros
- Grillas fijas en `configs/gate2.json`.
- Criterio: media de log loss en el bloque de ajuste, sobre la muestra común de la
  familia. Para M4: filas elegibles A.
- La configuración elegida se evalúa **una sola vez** en la prueba interna. Las demás
  configuraciones **no** se evalúan en la prueba interna.
- Reconocido: la evaluación dentro del bloque de ajuste es optimista (hiperparámetros
  elegidos con esos datos). Solo la prueba interna es fuera de muestra respecto de la
  selección.

### A5. Reglas de la escalera (decididas en el bloque de ajuste)

| Decisión | Regla |
|---|---|
| Construir/adoptar M2 sobre M1 | Δ(M2* − M1*) con U < 0 |
| Variables de tiros de M3 entran en M4-sport | Δ(M3 con tiros − M3 solo goles) con U < 0 |
| M5 binomial negativa | Índice de dispersión de goles totales respecto de M2* > 1,10, con límite inferior del IC95 > 1,05 |
| M5 Poisson bivariado | \|correlación residual local-visitante\| > 0,05 con IC95 excluyendo 0 |
| M5 gradient boosting | No en GATE 2, salvo no linealidad documentada en la calibración de M4-sport |

### A6. Evaluación en la prueba interna (de desarrollo, no veredicto)
- Muestra primaria: filas elegibles A (sin ambigüedad de captura) de 2014/15-2021/22 con
  predicción de todos los modelos.
- Métricas: Δ log loss pareada contra A y contra C; Brier; pendiente e intercepto de
  calibración; ECE; nitidez; AUC.
- Incertidumbre: bootstrap por bloques de 4 semanas (10.000 réplicas, semilla
  20261127); Diebold-Mariano con HAC.
- Clasificación con la partición del §6 del protocolo (δ = 0,001).
- Comparaciones clave: M1 frente a C; M2 frente a M1; M4-cal frente a A; **M4-sport
  frente a M4-cal**.
- Estabilidad: Δ por temporada; sensibilidad a configuraciones vecinas de la grilla;
  trayectorias de parámetros (η_d, a, b); proporción de ajustes sin convergencia.
- Potencia: σ_Δ de M4-sport − A y de M2* − A → MDE para el holdout (propuesta de δ).

### A7. Controles contra filtraciones (exigencia 5)

| Etapa | Control | Prueba |
|---|---|---|
| Entrenamiento | El motor entrega al modelo solo filas con `match_date < τ`. Lo verifica por aserción y registra `train_max_date` y `n_train` **por ajuste** en los fitlogs (corregido en GATE 2.1: los archivos de predicciones no los contienen; se enlazan por `config_id`, `block`, `scope` y `fit_tau`) | `test_walkforward_*`; `test_train_max_date_stored_per_fit_and_joinable` |
| Invariancia al futuro | Alterar resultados, estadísticas y cuotas de cierre de todos los partidos con fecha ≥ τ no cambia ninguna predicción hecha en τ | `test_*_invariant_to_future` (todos los modelos y features) |
| Transformaciones | Estandarización e imputación se ajustan en `fit` con filas de entrenamiento. La predicción de una fila no depende de las demás filas del lote | `test_batch_independence` |
| Features | EWMA con `merge_asof` estricto (`< info_cutoff_date`); comprobación por fuerza bruta | `test_features_*` |
| Selección de variables e hiperparámetros | Funciones que reciben solo el bloque de ajuste; se niegan si reciben temporadas de prueba interna; resultado invariante a alterar la prueba interna | `test_selection_*` |
| Calibración (M4-cal) | Ajustada en cada τ solo con filas < τ | Invariancia al futuro |
| Valla GATE 3 | El motor rechaza evaluar temporadas > 2021/22 salvo autorización ligada a los candidatos congelados; registra todo intento (GATE 2.1) | `test_fence_*`; `test_gate3_authorization_binding_and_logging` |

### A8. Trazabilidad (exigencias 6 y 7)
- **Todas** las predicciones fuera de muestra de **todas** las configuraciones (también
  las descartadas) se guardan en `experiments/gate2/predictions/*.parquet`, con
  `match_id`, `config_id`, `block`, `p_over` y `fit_tau` (los Poisson, además `lam_h` y
  `lam_a`). *Corrección GATE 2.1:* `train_max_date` **no** está en esos archivos; está en
  los fitlogs, un registro por ajuste, enlazable por (`config_id`, `block`, `scope`,
  `fit_tau`), donde `scope` es la división del partido o `pooled`.
- Cada ajuste registra tiempo, iteraciones, convergencia, `n_train` y `train_max_date`
  (`experiments/gate2/fitlogs/`). Cada etapa registra tiempo de pared, tiempo de CPU y
  memoria máxima (`experiments/gate2/runlog.json`).

### A9. Paquete de auditoría (exigencia 8)
Generador de datos sintéticos (`qsports.synthetic`) con verdad conocida y comando
`python -m qsports audit-synthetic`. Ejecuta todo el pipeline (walk-forward, M0-M4,
evaluador y pruebas de filtración) **sin** datos de la fuente ni datos sellados.

---

## Parte B — Resultados

Resultados de **desarrollo** (no son veredictos de Q1-Q3). Fuentes:
`experiments/gate2/results.json`, `stability.json`, `configs.json`, `runlog.json`.

### B0. Desviaciones de la Parte A
| Id | Desviación | Motivo | Momento |
|---|---|---|---|
| D-1 | Regla de extensión de borde de grilla (`configs/gate2.json → boundary_rule`) | La selección Poisson quedó en el borde de la grilla preregistrada (ridge y ventana máximos) | Tras ver solo la selección Poisson en ajuste; **antes** de ver M3, M4 o la prueba interna |
| D-2 | Optimizador Poisson: Newton-Raphson con Hessiana analítica en vez de L-BFGS | Velocidad (×7,6) y precisión; mismo modelo y mismo óptimo (prueba automática) | Antes de cualquier resultado |
| D-3 | M3 usó el **conteo lineal** de partidos previos (estandarizado), no `log(1 + partidos previos)` como dice A3 | Discrepancia entre especificación e implementación detectada por la auditoría de GATE 2 (no fue una decisión) | Detectada en GATE 2.1. Los resultados de GATE 2 corresponden a la forma lineal. Sensibilidad con `log1p` solo en el bloque de ajuste: `experiments/gate2_1/repro_run/results.json → m3_spec_sensitivity` |
| D-4 | El bootstrap formó bloques de semanas **activas**, no de semanas calendario como dice el protocolo §4 | Error de implementación detectado por la auditoría | Corregido en GATE 2.1; resultados con ambos métodos y sensibilidad a 2, 4, 8 y 12 semanas en `GATE_2_1_REPORT.md` |

### B1. Selecciones en el bloque de ajuste

| Familia | Seleccionado | Grilla final (tras D-1) | Nota |
|---|---|---|---|
| M1 | ventana 1.095 d, ridge 128 | ventanas {365, 730, 1.095, 1.642}; ridge {1…128} | **Sigue en el borde de ridge** tras las 3 extensiones permitidas (limitación) |
| M2 | semivida 480 d, ridge 64, sin prior de ascendidos | semivida {120, 240, 480, 960}; ridge {1…128} | Óptimo **interior**. El prior de ascendidos no mejora (0,685287 frente a 0,685269) |
| M3 | GSTC, EWMA 15 partidos, ridge 100 | ridge {1, 10, 100, 1000} | Las 6 mejores configuraciones difieren en < 1e-5 |
| M4-cal | semivida 730 d | {∞, 730} | 0,683855 frente a 0,683925 |
| M4-sport | semivida 730 d, ridge 1.000, X = [logit p_M2* − logit p_A] | ridge {10…10.000} | Óptimo interior; la regularización fuerte acerca M4-sport a M4-cal |

**Reglas de la escalera (§A5), bloque de ajuste:**
- M2 frente a M1: Δ = −0,00057 [−0,00080; −0,00035], S-NR → **M2 justificado**.
- H1b (tiros frente a solo goles, dentro de M3): Δ = −0,00003 [−0,00024; +0,00018], **EQ** →
  las variables de tiros **no** entran en M4-sport.
- M5 (diagnósticos con M2* en ajuste, n = 69.881): índice de dispersión 1,017 [1,005;
  1,030] < 1,10 → binomial negativa **no justificada**. Correlación residual local-visitante
  0,0135 [0,0055; 0,0216]: distinta de 0, pero |r| < 0,05 → Poisson bivariado **no
  justificado**. Gradient boosting: sin no linealidad documentada (pendiente de calibración
  de M4-sport = 1,005) → **no justificado**. **Ningún modelo M5 se implementó** (exigencia 9).

### B2. Prueba interna 2014/15-2021/22 (una evaluación por familia; n = 61.137 filas elegibles A)

| Comparación (modelo − referencia) | Δ log loss | IC95 bootstrap por bloques | Categoría |
|---|---:|---|:---:|
| M1 − C | −0,00520 | [−0,00597; −0,00442] | S-R |
| M2 − C | −0,00593 | [−0,00677; −0,00510] | S-R |
| M3 − C | −0,00519 | [−0,00584; −0,00450] | S-R |
| M2 − M1 | −0,00073 | [−0,00098; −0,00047] | S-NR |
| M3 − M2 | +0,00075 | [+0,00017; +0,00133] | I-NR |
| **M2 − A** | **+0,00480** | [+0,00398; +0,00562] | **I-R** |
| M3 − A | +0,00554 | [+0,00462; +0,00649] | I-R |
| M4-cal − A | −0,00008 | [−0,00020; +0,00004] | EQ |
| M4-sport − A | −0,00009 | [−0,00022; +0,00004] | EQ |
| **M4-sport − M4-cal** | **−0,00001** | **[−0,00006; +0,00004]** | **EQ** |
| A − C | −0,01073 | [−0,01198; −0,00953] | S-R |

Log loss medio: A 0,67841; M4-cal 0,67833; M4-sport 0,67832; M2 0,68321; C 0,68914.
Pendiente de calibración: A 1,103 (probabilidades ligeramente comprimidas); M4-cal 1,003;
M2 1,008.

**Lectura de desarrollo:**
1. Los modelos deportivos superan a la frecuencia histórica (S-R), pero son claramente
   **peores que el mercado** (M2 − A: I-R, en todas las temporadas y en ambos regímenes).
2. Recalibrar el mercado (M4-cal) corrige su pendiente, pero no mejora el log loss de forma
   distinguible (EQ).
3. **Aporte deportivo incremental de M4-sport (desviación logit p_M2* − logit p_A): no
   demostrado** en 2014/15-2021/22. Δ(M4-sport − M4-cal) es EQ, con un IC cuya amplitud
   (±0,00005) excluye una mejora del orden de δ = 0,001 para esa formulación. Igual en
   Betbrain (2014/15-2018/19) y Oddsportal (2019/20-2021/22). *Alcance (GATE 2.1):* no se
   evaluaron otras variables (xG, alineaciones, lesiones), otras formulaciones ni otros
   períodos; la equivalencia predictiva no implica nada sobre la rentabilidad (Q3).

### B3. Potencia para el holdout (supuestos en `EXPERIMENTAL_PROTOCOL.md` §5)
N elegible en el holdout (conteo de nivel 0) = 15.154. MDE (α = 5% bilateral, potencia
80%): M4-sport − A = 0,00036; M4-sport − M4-cal = 0,00014; M4-cal − A = 0,00033; M2 − A =
0,00216 nats. Con δ = 0,001, el holdout tiene potencia suficiente para las comparaciones
de M4, pero **no** para detectar mejoras de tamaño δ de M2 frente al mercado.

### B4. Estabilidad, convergencia y consumo (`experiments/gate2/stability.json`)
- Δ por temporada: M2 − A positivo en las 8 temporadas (+0,0028 a +0,0064); M4-cal − A y
  M4-sport − M4-cal entre −0,0003 y +0,0001.
- Configuraciones vecinas: diferencias de log loss < 0,0004 (M1, M2) y < 1e-5 (M3).
- Localía η de M2: de ~0,29 (2005-2011) a ~0,19 (2020/21-2021/22).
- Coeficiente b de M4: entre 1,00 y 1,23; β deportivo: de −0,02 a 0,05.
- Ajustes: ~474.500 (M1 216.819; M2 234.249; M3 5.705; M4 1.376; M0 16.374). Sin
  convergencia formal: M1 0,029%, M2 0,070% (gradiente ≤ 2·10⁻⁵, precisión límite;
  impacto medido ≤ 2,1·10⁻⁹ en p); M3 y M4: 0.
- Tiempo de ajuste mediano: Poisson 6-9 ms; M3 80 ms; M4 13-16 ms. Memoria máxima del
  proceso principal: 1,66 GB.

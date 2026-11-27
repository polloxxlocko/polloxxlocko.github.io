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
| Entrenamiento | El motor entrega al modelo solo filas con `match_date < τ`. Lo verifica por aserción y registra `train_max_date` por predicción | `test_walkforward_*` |
| Invariancia al futuro | Alterar resultados, estadísticas y cuotas de cierre de todos los partidos con fecha ≥ τ no cambia ninguna predicción hecha en τ | `test_*_invariant_to_future` (todos los modelos y features) |
| Transformaciones | Estandarización e imputación se ajustan en `fit` con filas de entrenamiento. La predicción de una fila no depende de las demás filas del lote | `test_batch_independence` |
| Features | EWMA con `merge_asof` estricto (`< info_cutoff_date`); comprobación por fuerza bruta | `test_features_*` |
| Selección de variables e hiperparámetros | Funciones que reciben solo el bloque de ajuste; se niegan si reciben temporadas de prueba interna; resultado invariante a alterar la prueba interna | `test_selection_*` |
| Calibración (M4-cal) | Ajustada en cada τ solo con filas < τ | Invariancia al futuro |
| Valla GATE 3 | El motor rechaza evaluar temporadas > 2021/22 | `test_fence_*` |

### A8. Trazabilidad (exigencias 6 y 7)
- **Todas** las predicciones fuera de muestra de **todas** las configuraciones (también
  las descartadas) se guardan en `experiments/gate2/predictions/*.parquet`, con
  `match_id`, `config_id`, `p_over`, `fit_tau` y `train_max_date`.
- Cada ajuste registra tiempo, iteraciones, convergencia y tamaño de entrenamiento
  (`experiments/gate2/fitlogs/`). Cada etapa registra tiempo de pared, tiempo de CPU y
  memoria máxima (`experiments/gate2/runlog.json`).

### A9. Paquete de auditoría (exigencia 8)
Generador de datos sintéticos (`qsports.synthetic`) con verdad conocida y comando
`python -m qsports audit-synthetic`. Ejecuta todo el pipeline (walk-forward, M0-M4,
evaluador y pruebas de filtración) **sin** datos de la fuente ni datos sellados.

---

## Parte B — Resultados

*(Se completa al terminar los experimentos; ver `GATE_2_REPORT.md`.)*

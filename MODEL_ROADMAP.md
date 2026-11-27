# MODEL_ROADMAP — Secuencia de modelos

> **Estado tras GATE 2 (2026-11-27):** M0-M4 implementados y evaluados en desarrollo; M5 **no**
> implementado (diagnósticos bajo umbral). Resultados en `MODEL_SPECIFICATION.md` Parte B y
> `GATE_2_REPORT.md`. El diseño original se conserva abajo.

Versión 1.0 · 2026-11-27 · GATE 1

**Regla de progresión:** un modelo de nivel superior solo se adopta si mejora al anterior
en la métrica primaria (Δ log loss pareada) en el **desarrollo interno** (walk-forward
2005/06-2021/22), con IC95 por bloques que excluya 0. Si no, se registra como resultado
negativo y se conserva el modelo más simple. No se presupone que la complejidad mejore.

Todos los modelos usan **solo** `process.load_dev()` (con la guarda anti-reservados) y
respetan `info_cutoff_date`.

## M0 — Baselines (Q1 y Q2)
- **M0a — Frecuencia histórica por competición:** benchmark C (ya implementado).
  Variante preregistrada: ventana móvil de las últimas 2 temporadas.
- **M0b — Mercado sin margen:** benchmark A (ya implementado). Es el estándar que M1-M5
  deben batir en Q2.

## M1 — Poisson independiente (estático por ventana)
`log λ_home = μ_d + η_d + att_h − def_a`,  `log λ_away = μ_d + att_a − def_h`;
`P(Over 2,5) = 1 − e^{−λ}(1 + λ + λ²/2)` con `λ = λ_home + λ_away` (exacto, sin truncamiento).
- **Parámetros por competición:** intercepto μ_d y localía η_d por división.
- **Identificabilidad:** restricción de suma cero de `att` y `def` dentro de cada
  división-ventana. Alternativa equivalente: penalización ridge, que fija la escala.
- **Regularización:** L2 sobre att/def (equivale a un prior gaussiano). λ_reg elegido en
  el desarrollo interno.
- **Estimación:** máxima verosimilitud penalizada (L-BFGS, SciPy). Se reajusta en cada
  captura con partidos anteriores al corte.
- **Advertencia:** Dixon-Coles no cambia P(Over 2,5) con intensidades fijas. Si se prueba,
  es solo por su efecto en la estimación de parámetros.

## M2 — Poisson dinámico
- **Ponderación temporal:** pesos `w = exp(−ξ·Δt)` (Dixon-Coles 1997; Ley et al. 2019),
  con ξ elegido en el desarrollo interno.
- **Alternativa de estado-espacio:** att/def como paseos aleatorios (Koopman y Lit 2015),
  solo si la ponderación no basta.
- **Cambio de temporada:** contracción de att/def hacia 0 entre temporadas (factor
  estimado) y μ_d/η_d con deriva lenta.
- **Ascensos y descensos:** la identidad de equipo se conserva entre divisiones del mismo
  país (nombre canónico tras alias). El equipo que llega de la división inferior empieza
  con sus parámetros previos ajustados por la diferencia de μ entre divisiones. El que
  entra desde fuera de las 22 divisiones (p. ej. a EC o SC3) recibe el promedio de los
  ascendidos previos de esa división. Todo estimado con datos anteriores al corte.

## M3 — Regresión logística regularizada (modelo independiente, sin mercado)
Predicción directa de `1{Over 2,5}` con variables **disponibles antes del partido**:
- Medias ponderadas exponencialmente (point-in-time) de goles a favor y en contra, tiros,
  tiros a puerta y córners por equipo, como local y visitante.
- Log-intensidad total de M1/M2 como variable (apilamiento simple).
- Interceptos por división (o efectos con partial pooling).
- Días de descanso desde el partido anterior (calculados con fechas pasadas).
- **Disponibilidad desigual de estadísticas:** completas en las 22 divisiones solo desde
  2017/18. Antes, solo en ~10 divisiones. Se preregistra el tratamiento: indicador de
  faltante + imputación con la media de la división calculada en la ventana de
  entrenamiento, **y** un análisis restringido a división-temporadas con ≥ 90% de
  estadísticas.
- Regularización L2 o elastic net, elegida en el desarrollo interno. Ablación variable a
  variable (base + 1) con walk-forward.
- Banderas de calidad (`flag_shots_target_gt_shots`, `flag_red_cards_gt_5`): las filas
  marcadas se excluyen del cálculo de medias móviles.

## M4 — Modelo asistido por mercado
`logit(p) = logit(p_A) + f(X)`
- **M4-null:** f ≡ 0 (el mercado mismo). Es el caso nulo contra el que se mide la
  información incremental.
- **M4-cal:** `logit(p) = a + b·logit(p_A)`. Recalibración pura del mercado (p. ej. sesgo
  favorito-longshot) **sin información deportiva**. Separa "mejorar el mercado por
  calibración" de "aportar información deportiva".
- **M4-sport:** `logit(p) = a + b·logit(p_A) + βᵀX`, con X = desviaciones de M2/M3
  respecto del mercado y variables de tiros, con penalización ridge fuerte (encoge hacia el
  mercado). Variante a priori: cuotas 1X2 pre-cierre como información de fuerza relativa.
- La información deportiva es **incremental** solo si M4-sport mejora a M4-cal (no solo a
  M4-null) en el desarrollo interno.

## M5 — Extensiones (solo tras evaluar M0-M4)
Binomial negativa (en desarrollo la razón varianza/media del total es ≈ 1,01, así que la
sobredispersión no es prioritaria); modelos jerárquicos bayesianos (PyMC, solo si se
justifica); Poisson bivariado (dependencia entre goles); gradient boosting
(LightGBM/XGBoost) con restricciones de calibración; ensambles. Cada extensión debe
demostrar mejora incremental fuera de muestra.

## Heterogeneidad entre competiciones
- Interceptos y localía específicos por división, con partial pooling hacia la media de
  su país o nivel cuando la evidencia es escasa (divisiones pequeñas: SC1-SC3 con 10
  equipos).
- Tasas de anotación distintas por división (μ_d) con deriva temporal.
- No se asume que los partidos son idénticamente distribuidos entre divisiones.
- **Evaluación:** global ponderada por partido (principal) y por división (descriptiva,
  con FDR), nunca usada para seleccionar ligas.

## Entregables por modelo (GATE 2-3)
Especificación en `MODEL_SPECIFICATION.md`, entrada en `EXPERIMENT_LOG.md`, predicciones
walk-forward guardadas en `experiments/` con hash de configuración y datos, y métricas con
IC por bloques.

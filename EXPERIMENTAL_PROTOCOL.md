# EXPERIMENTAL_PROTOCOL — Protocolo experimental preliminar

Versión 0.9 (preliminar) · 2026-11-27 · GATE 1

Este protocolo se diseña **antes de entrenar cualquier modelo**. Se congelará (hash en
`PROTOCOL_FREEZE.json`) al final de GATE 4 y antes de solicitar la apertura del holdout.
Desde hoy, todo cambio se anota en `EXPERIMENT_LOG.md` con su motivo.

## 1. Tres preguntas separadas

| # | Pregunta | Referencia | Muestra |
|---|---|---|---|
| **Q1** | ¿El modelo estima probabilidades mejor que una referencia estadística simple? | **C** (frecuencia histórica point-in-time) | Muestra primaria A (mismas filas que Q2) |
| **Q2** | ¿El modelo mejora las probabilidades del mercado con información comparable? | **A** (consenso pre-cierre sin margen) | Muestra primaria A |
| **Q3** | ¿Esa mejora se traduce en rentabilidad simulada con cuotas realmente observadas? | Precios pre-cierre observados (Bet365 pre; promedio pre) | Muestra primaria A ∩ precio disponible |

Reglas de interpretación:
- Una respuesta afirmativa **no implica** las demás. Q1 positiva es lo esperable y no dice
  nada sobre el mercado.
- Q2 positiva no implica Q3, porque el margen de la casa puede absorber la mejora.
- Q3 positiva con Q2 no demostrada se interpreta como **probable azar**.
- **Coolbet:** sin cuotas históricas. Ningún resultado de Q3 se extrapola a Coolbet.

## 2. Diseño temporal

| Bloque | Temporadas | Uso |
|---|---|---|
| Burn-in | 2000/01-2004/05 | Solo para inicializar fuerzas de equipos; sin evaluación |
| **Desarrollo interno** | 2005/06-2021/22 | Walk-forward: selección de variables, hiperparámetros, calibradores, umbrales, estructura del modelo |
| **Validación de desarrollo** | 2022/23-2023/24 | Comparación de candidatos **congelados**; elección del modelo primario. Cada familia candidata se evalúa aquí **una vez** |
| **Prueba final (holdout)** | 2024/25-2025/26 | **Una sola** evaluación del modelo primario preregistrado, tras autorización |
| Prospectivo | 2026/27+ | GATE 5 (predicciones registradas antes de cada partido) |

**Walk-forward (todas las fases).** Para cada fecha de captura τ (viernes o martes), el
modelo se ajusta con los partidos con `match_date < τ` y predice todos los partidos cuya
captura estimada es τ. Por eficiencia, los parámetros pueden reajustarse con menor
frecuencia (p. ej. cada 4 capturas). En ese caso se usa el último ajuste con fecha ≤ τ,
lo que nunca viola el corte de información. Prohibida la división aleatoria.

**Validación anidada:** los hiperparámetros se eligen con walk-forward **dentro** del
desarrollo interno, nunca con la validación de desarrollo ni con el holdout.

## 3. Métricas

**Primaria:** diferencia pareada de log loss contra el benchmark A:
`Δ_i = LL_modelo,i − LL_A,i`, con `LL = −[y·ln p + (1−y)·ln(1−p)]` (nats). Media global
ponderada por partido sobre la muestra primaria. Δ̄ < 0 significa que el modelo es mejor.

**Secundarias:** Brier y su diferencia pareada; pendiente e intercepto de calibración
(regresión logística de y sobre logit(p)); curvas de fiabilidad (10 bins de igual
frecuencia); ECE; nitidez (desviación estándar de p, media de |p − 0,5|); discriminación
(AUC); CLV frente al cierre B; ROI simulado (Q3).

**Evaluación por competición:** complementaria y descriptiva. Las 22 divisiones se
reportan con control FDR (Benjamini-Hochberg). **Prohibido** usar resultados
desagregados para seleccionar ligas.

## 4. Incertidumbre

- **Bootstrap por bloques de semanas:** los partidos se agregan por semana calendario
  (todas las ligas juntas, para capturar shocks comunes de una misma jornada) y se
  remuestrean bloques móviles de 4 semanas consecutivas (dependencia serial: fuerzas de
  equipo persistentes). 10.000 réplicas, semilla fija. Intervalos percentil al 95%.
- **Diebold-Mariano** con varianza HAC (Newey-West) sobre la serie semanal de Δ̄.
- **Sensibilidad:** bootstrap por clusters de división-temporada.
- Ningún rango se rotula como intervalo de confianza si su método no lo justifica.

## 5. Potencia y tamaño de muestra (supuestos documentados)

Fórmula: `MDE = (z_{1−α/2} + z_{1−β}) · σ_Δ · √deff / √N`.

Estimación preliminar con un sustituto (desarrollo interno 2005/06-2021/22,
n = 130.862, sin modelos entrenados), usando Δ = LL_C − LL_A:
- σ_Δ = 0,114 nats; efecto de diseño por semana (deff) = 1,23.
- Log loss medio: A = 0,6812, C = 0,6894.
- Con N ≈ 15.000 (holdout; conteo de nivel 0: 15.328 filas): **MDE ≈ 0,0029 nats**
  (α = 5% bilateral, potencia 80%).
- Supuesto clave: σ_Δ depende del modelo. Un modelo cercano al mercado (M4) tendrá un
  σ_Δ mucho menor, y por tanto un MDE menor. σ_Δ se re-estimará para el candidato
  congelado en la validación de desarrollo, antes del congelamiento.
- Supuestos: independencia entre semanas no adyacentes; dependencia intra-semana
  capturada por deff; estacionariedad aproximada de σ_Δ entre regímenes.

## 6. Criterios de decisión (preregistrados; los umbrales se confirman al congelar)

Sean Δ̄ e IC95 los del holdout, calculados con el método de §4. **SESOI** (mínimo efecto
de interés) provisional = **0,001 nats por partido**, ≈0,15% del log loss del mercado. Se
confirma o ajusta al congelar con la potencia del §5, y **nunca después** de abrir el
holdout.

| Pregunta | ÉXITO | FRACASO | INCONCLUSO |
|---|---|---|---|
| Q1 (vs C) | IC95 superior < 0 | IC95 inferior > −SESOI | Otros casos |
| Q2 (vs A) | IC95 superior < 0 **y** Δ̄ < 0 también en la validación de desarrollo **y** calibración aceptable (\|pendiente − 1\| < 0,2; \|intercepto\| < 0,05) | IC95 inferior > −SESOI (se descartan mejoras relevantes) | Otros casos → **VENTAJA ESTADÍSTICA NO DEMOSTRADA** |
| Q3 (económica) | Q2 = éxito **y** IC95 inferior del ROI > 0 con la regla de apuesta fijada en desarrollo, con precios Bet365 pre | IC95 superior del ROI < 0 | Otros casos (lo más probable por potencia) |

Condiciones adicionales:
- **Un único modelo primario** se declara al congelar. Los modelos y métricas
  secundarios se reportan con corrección de Holm y la etiqueta "exploratorio".
- La regla de selección de apuestas (umbral de EV, tope de cuota 3,50, apuesta fija) se
  fija en el desarrollo interno, se verifica en la validación y no se cambia después.
- Un CLV positivo o una mejora de log loss **no** son prueba suficiente de rentabilidad.

## 7. Análisis de sensibilidad preregistrados

1. Por régimen de la fuente: Betbrain (2005/06-2018/19) frente a Oddsportal (2019/20+).
   El holdout es enteramente Oddsportal.
2. Excluyendo los 22.946 partidos de viernes/martes sin hora (captura no verificable).
3. Corte de información desplazado 1 día antes.
4. Eliminación del margen por método de potencia en vez de proporcional.
5. Benchmarks alternativos: A′-Bet365 y A* (consenso de casas individuales) sobre
   muestras idénticas.
6. Excluyendo filas con banderas de calidad (`flag_*`) en modelos que usan estadísticas.
7. Con y sin los alias de equipos marcados como juicio (J).

## 8. Registro y control de selección múltiple

- Cada ejecución registra en `EXPERIMENT_LOG.md`: id, fecha, hipótesis, configuración
  (hash), versión del dataset (`MANIFEST.json`), bloques usados, métricas, resultado
  (incluido el negativo) y decisión.
- Se lleva la cuenta del número de variantes evaluadas en la validación de desarrollo.
  Si se comparan más de 3 familias, se aplica el test SPA de Hansen (o Reality Check de
  White) contra el benchmark A.
- Prohibido reportar solo el mejor resultado.

## 9. Congelamiento

Se congela al final de GATE 4: este documento, `MARKET_BENCHMARK_SPECIFICATION.md`,
`configs/*.json`, el código del modelo primario y sus parámetros, la regla de apuestas y el
SESOI. Procedimiento de apertura en `HOLDOUT_PROTECTION_PROTOCOL.md` §6.

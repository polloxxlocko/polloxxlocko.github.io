# EXPERIMENTAL_PROTOCOL — Protocolo experimental preliminar

Versión 0.10 (preliminar) · 2026-11-27 · revisado al inicio de GATE 2 (§2, §6, §10)

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
| **Desarrollo interno — ajuste** (GATE 2) | 2005/06-2013/14 | Hiperparámetros, selección de variables, decisión de escalar complejidad |
| **Desarrollo interno — prueba interna** (GATE 2) | 2014/15-2021/22 | Una evaluación por familia ya ajustada; reglas de adopción de `MODEL_SPECIFICATION.md` |
| **Validación de desarrollo** (GATE 3) | 2022/23-2023/24 | Comparación de candidatos **congelados**; elección del modelo primario. Cada familia candidata se evalúa aquí **una vez**. **Vallado en GATE 2** (el motor walk-forward se niega a evaluarlo) |
| **Prueba final (holdout)** | 2024/25-2025/26 | **Una sola** evaluación del modelo primario preregistrado, tras autorización |
| **Reserva histórica sellada** | 2026/27 (partidos ya disputados al descargar) | Sellada. **No es validación prospectiva**: sus resultados ya existían antes de registrar predicciones (§10) |
| **Validación prospectiva genuina** (GATE 5) | Partidos futuros | Solo predicciones registradas y publicadas **antes** de cada partido (§10) |

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

## 6. Criterios de decisión (revisados en GATE 2: categorías mutuamente excluyentes)

**Notación.** Δ̄ = diferencia media pareada (modelo − referencia) de log loss sobre la
muestra de la pregunta; **[L, U]** = intervalo bootstrap por bloques al 95% bilateral
(§4); **δ** = SESOI, el mínimo efecto de interés práctico. δ provisional = **0,001 nats
por partido** (≈0,15% del log loss del mercado). Se fija al congelar el protocolo con la
potencia del §5 y **nunca** se modifica después de abrir el holdout. Δ̄ < 0 significa que
el modelo es mejor. Exigir U < 0 equivale a una prueba unilateral al 2,5%.

**Partición** (L ≤ U siempre; cada resultado cae en **exactamente una** categoría):

| Código | Categoría | Condición sobre [L, U] | Lectura |
|---|---|---|---|
| **S-R** | Superioridad estadística y relevante | U < −δ | Mejora distinguible del azar y mayor que δ con alta confianza |
| **S-NR** | Superioridad estadística, relevancia no demostrada | −δ ≤ U < 0 | Mejora distinguible del azar; no se puede afirmar que supere δ |
| **EQ** | Equivalencia práctica | L ≤ 0 ≤ U, L > −δ y U < δ | Sin diferencia distinguible y cualquier diferencia plausible es menor que δ |
| **INC** | Inconcluso | L ≤ 0 ≤ U y (L ≤ −δ o U ≥ δ) | Los datos no permiten distinguir entre mejora relevante, equivalencia o empeoramiento |
| **I-NR** | Inferioridad estadística, relevancia no demostrada | 0 < L ≤ δ | Peor que la referencia; no se puede afirmar que el empeoramiento supere δ |
| **I-R** | Inferioridad estadística y relevante | L > δ | Peor que la referencia en más de δ con alta confianza |

Verificación de la partición: S-R y S-NR exigen U < 0; I-NR e I-R exigen L > 0; EQ e INC
exigen L ≤ 0 ≤ U y se separan por la posición de L y U respecto de ±δ. Los rangos no se
solapan y cubren todos los casos. La función `qsports.evaluation.decision_category`
implementa esta tabla y sus pruebas automáticas recorren los bordes.

**Veredictos por pregunta** (holdout):

| Pregunta | Referencia | Veredicto afirmativo | Veredicto negativo | Resto |
|---|---|---|---|---|
| **Q1** | C (frecuencia histórica) | S-R: "mejora relevante sobre una referencia simple"; S-NR: "mejora estadística de magnitud incierta" | EQ, I-NR, I-R: "no mejora a una referencia simple" | INC: **EVIDENCIA INSUFICIENTE** |
| **Q2** | A (consenso pre-cierre) | S-R o S-NR **y** las 3 condiciones de validez | EQ, I-NR, I-R → **VENTAJA ESTADÍSTICA NO DEMOSTRADA** (con la categoría explícita) | INC → **VENTAJA ESTADÍSTICA NO DEMOSTRADA / EVIDENCIA INSUFICIENTE** |
| **Q3** | ROI = 0 con precios observados | Misma partición aplicada a **−ROI**, con δ_ROI = 0,01 por unidad apostada (S-R ⇔ límite inferior del IC del ROI > 0,01; S-NR ⇔ 0 < límite inferior ≤ 0,01). Afirmativo solo con S-R o S-NR **y** Q2 afirmativo | EQ, I-NR, I-R | INC (lo más probable por potencia) |

**Condiciones de validez de Q2** (si alguna falla, el veredicto es **VENTAJA ESTADÍSTICA
NO DEMOSTRADA**, se reporta la categoría y se indica qué condición falló):
1. Dirección consistente: Δ̄ < 0 también en la validación de desarrollo (2022/23-2023/24).
2. Calibración aceptable en el holdout: |pendiente − 1| < 0,2 y |intercepto| < 0,05.
3. El modelo evaluado es el único modelo primario declarado al congelar.

**Información incremental deportiva** (comparación clave de M4, ver
`MODEL_SPECIFICATION.md`): la misma partición se aplica a Δ(M4-sport − M4-cal). Solo
**S-R o S-NR** permite afirmar que las variables deportivas aportan información más allá
de recalibrar el mercado. EQ, INC o inferioridad → "aporte deportivo incremental **no
demostrado**".

Condiciones adicionales:
- Los modelos y métricas secundarios se reportan con corrección de Holm y la etiqueta
  "exploratorio".
- La regla de selección de apuestas (umbral de EV, tope de cuota 3,50, apuesta fija) se
  fija en el desarrollo interno, se verifica en la validación y no se cambia después.
- Un CLV positivo o una mejora de log loss **no** son prueba suficiente de rentabilidad.
- En GATE 2 estas categorías se calculan sobre la prueba interna (2014/15-2021/22) con
  carácter **de desarrollo**: no constituyen veredictos de Q1-Q3.

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

## 10. Reserva histórica sellada frente a validación prospectiva genuina

| | Reserva histórica sellada (2026/27) | Validación prospectiva genuina (GATE 5) |
|---|---|---|
| Partidos | Disputados y descargados el 2026-11-27 (2.680 filas) o los que se descarguen después del hecho | Partidos que aún no se han jugado cuando se registra la predicción |
| ¿Existían los resultados antes de predecir? | **Sí** (están en disco, sellados) | **No** |
| Garantía contra el uso de resultados | Procedimental (sello, guardas, log de accesos) | **Temporal y verificable por terceros**: la predicción existe antes del evento |
| Uso permitido | Evaluación retrospectiva adicional, solo con autorización, después del holdout | Evaluación prospectiva principal (Q1-Q3) en GATE 5 |

**Protocolo mínimo de la validación prospectiva genuina** (se detallará en GATE 5):
1. Modelo, código y parámetros congelados con hash (commit git).
2. Para cada partido: predicción generada con datos hasta la captura pre-cierre y
   registrada en un archivo append-only con `match_id`, probabilidad, cuota observada y
   fuente, momento de registro UTC, hash del modelo y versión de los datos.
3. **Publicación antes del inicio** (commit firmado y push a un repositorio remoto). La
   marca de tiempo de GitHub sirve como testigo externo. Una predicción registrada
   después del inicio queda **inválida** y se excluye, sin reemplazo.
4. Evaluación al cierre del período preregistrado, con los mismos criterios del §6.
5. Ningún resultado de la reserva histórica 2026/27 se presenta como prospectivo.


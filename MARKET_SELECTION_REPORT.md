# MARKET_SELECTION_REPORT — Selección del mercado (GATE 0)

Versión 1.0 · 2026-11-27 · **Requiere aprobación del usuario**

## 1. Recomendación

> **Mercado recomendado: Fútbol — Over/Under 2,5 goles (tiempo reglamentario), con un
> universo de competiciones preregistrado: las 22 divisiones de Football-Data.co.uk, sin
> selección retrospectiva de ligas.**

**Nivel de confianza en la recomendación: moderado.**
- La matriz ponderada da un **empate exacto** con 1X2 (4,55 frente a 4,55). Con pesos
  aleatorios, el reparto es ≈50/50.
- El desempate se basa en **criterios secundarios medidos con datos**, declarados
  explícitamente como secundarios (§5). Favorecen a O/U 2,5 con claridad.
- La recomendación es sobre **viabilidad de investigación**. **No** implica que exista una
  ventaja explotable. La evidencia previa (§6) sugiere que, para un usuario de una sola
  casa, H2 (rentabilidad) es poco probable. Este proyecto debe estar preparado para
  concluir **VENTAJA ESTADÍSTICA NO DEMOSTRADA**.

## 2. Universo inicial y descarte preliminar

Se evaluaron los 9 candidatos del encargo con la matriz del §3. Los 3 de mayor puntaje
pasaron a evaluación profunda:

1. Fútbol O/U 2,5 (4,550)
2. Fútbol 1X2 (4,550)
3. NBA ganador del partido (3,050)

Descartes con su motivo principal:
- **Córners y tarjetas:** **NO ELEGIBLES**. No se encontró ninguna fuente de cuotas
  históricas verificable. La regla del encargo impide su validación económica aunque sus
  estadísticas son buenas. Además, no hay estudios de eficiencia de mercado. En tarjetas,
  el árbitro solo consta en el 44% de los partidos y las definiciones varían entre países.
- **NBA total de puntos:** el archivo gratuito tiene la línea pero **no el precio**, y
  suponer -110 sería una cuota ficticia. Los precios reales son de pago desde 2020.
- **NBA props (rebotes, asistencias, puntos):** cuotas solo de pago desde may-2023, sin
  literatura de eficiencia, pipeline de minutos y lesiones complejo y costoso.

## 3. Matriz de selección

Puntajes 0-5 según la rúbrica de `configs/market_selection_matrix.json`, que contiene la
justificación de cada celda. Tipo de evidencia: **E** empírica verificada en esta sesión,
**T** evaluación técnica, **J** juicio experto, **ND** información no disponible.

| Mercado | C1 Cuotas (25%) | C2 Estadísticas (20%) | C3 Backtest (20%) | C4 Modelos (15%) | C5 Ineficiencias (10%) | C6 Coste (10%) | Total | Elegible |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| Fútbol — O/U 2,5 | 5 [E] | 4 [E] | 5 [E] | 5 [E] | 2,5 [E] | 5 [E] | **4,550** | Sí |
| Fútbol — 1X2 | 5 [E] | 4 [E] | 5 [E] | 5 [E] | 3 [E] | 4,5 [J] | **4,550** | Sí |
| NBA — Ganador | 3 [E] | 3 [T] | 3 [T] | 4 [E] | 2,5 [E] | 2,5 [E] | **3,050** | Sí |
| NBA — Total de puntos | 2,5 [E] | 3 [T] | 3 [T] | 4 [T] | 2 [E] | 2,5 [E] | **2,875** | Sí |
| Fútbol — Córners | 1,5 [E] | 3,5 [E] | 1,5 [T] | 4 [T] | 1 [ND] | 2 [T] | **2,275** | **No** |
| Fútbol — Tarjetas | 1,5 [E] | 2,5 [E] | 1,5 [T] | 3,5 [T] | 1 [ND] | 2 [T] | **2,000** | **No** |
| NBA — Rebotes | 2 [E] | 2 [T] | 2 [T] | 3 [T] | 1 [ND] | 1 [T] | **1,950** | Sí |
| NBA — Asistencias | 2 [E] | 2 [T] | 2 [T] | 3 [T] | 1 [ND] | 1 [T] | **1,950** | Sí |
| NBA — Puntos individuales | 2 [E] | 2 [T] | 2 [T] | 3 [T] | 1 [ND] | 1 [T] | **1,950** | Sí |

Justificación resumida de las celdas decisivas:
- **C1 = 5 en ambos de fútbol:** cuotas gratuitas descargadas y verificadas, pre-cierre y
  cierre desde 2019/20 (~56.000 partidos con cierre) y pre-cierre desde 2005/06
  (`DATA_FEASIBILITY_REPORT.md` §2.4).
- **C5 (O/U 2,5) = 2,5:** una sola línea de investigación (Wheatcroft 2020, 2021). La
  rentabilidad publicada exige cuotas máximas y con cuotas promedio hay pérdida.
- **C5 (1X2) = 3:** literatura más amplia pero mixta y mayormente antigua.
- **C6 (1X2) = 4,5 [J]:** la única celda de juicio en los dos finalistas. El mercado de
  tres resultados complica algo la eliminación de margen y la calibración.

Un puntaje bajo en C5 por **ND** significa *ausencia de evidencia encontrada*, no
evidencia de eficiencia.

## 4. Análisis de sensibilidad

`phase0/market_selection.py`, semilla 20261127, 20.000 simulaciones por escenario.

| Escenario | P(1.º = O/U 2,5) | P(1.º = 1X2) | 3.º lugar |
|---|---:|---:|---|
| Pesos base | empate exacto | empate exacto | NBA ganador |
| Pesos iguales (1/6) | empate exacto (4,417) | empate exacto | NBA ganador |
| Dirichlet concentrado (k=100) | 50,3% | 49,7% | NBA ganador (100%) |
| Dirichlet disperso (k=20) | 49,6% | 50,4% | NBA ganador (100%) |
| Perturbación ±0,5 de celdas T/J/ND | 49,3% | 50,7% | NBA ganador 91,9% / NBA total 8,1% |
| Combinado (Dirichlet k=20 + perturbación) | 44,4% | 55,6% | NBA ganador 88,0% / NBA total 12,0% |

Sensibilidad de un factor a la vez (±5 y ±10 puntos porcentuales sobre cada peso,
renormalizando el resto):
- C1, C2, C3 y C4: el empate se mantiene (ambos tienen el mismo puntaje en esos criterios).
- **C5 ↑** (más peso a la literatura) → gana 1X2 por 0,03-0,06.
- **C6 ↑** (más peso a simplicidad y coste) → gana O/U 2,5 por 0,03-0,06.

**Conclusión de sensibilidad:**
1. Los dos mercados de fútbol dominan robustamente (100% de los escenarios en el top-2).
2. Ninguno de los mercados NBA se acerca al primer lugar.
3. **La matriz no discrimina entre O/U 2,5 y 1X2.** El orden depende de cuánto pesan
   la literatura frente a la simplicidad.

## 5. Desempate: criterios secundarios empíricos

Los siguientes criterios no están en la matriz original. Se declaran explícitamente como
**criterios secundarios de desempate**. Se calcularon solo con cuotas de cierre de Bet365
(2019/20-2026/27, ~56.000 partidos por mercado) y **sin usar resultados**:

| Criterio | O/U 2,5 | 1X2 | Favorece |
|---|---:|---:|---|
| Precios ≤ 3,50 (cuota máxima habitual del usuario) | **99,5%** | 66,6% | O/U |
| Precio mediano de los resultados ≤ 3,50 | 1,91 | 2,63 | — |
| Desviación estándar del retorno por unidad apostada (precios ≤ 3,50) | **0,97** | 1,24 | O/U |
| Apuestas para detectar ROI = 2% (unilateral α=0,05, potencia 0,80, independencia) | **~14.700** | ~23.600 | O/U |
| Apuestas para detectar ROI = 3% | ~6.500 | ~10.500 | O/U |
| Margen mediano de cierre Bet365 | 5,8% | 6,2% | O/U (leve) |
| Estructura | Binaria (EV, calibración y CLV directos) | Tres resultados | O/U |
| Literatura de modelos | Directa (Poisson → fórmula analítica) | Directa | Empate |
| Evidencia previa de ineficiencia | Más débil | Más amplia | 1X2 |

**Interpretación:** O/U 2,5 necesita ~38% menos apuestas que 1X2 para detectar la misma
ventaja. Además, casi todos sus precios caben dentro del tope de 3,50 del usuario, frente a
dos tercios en 1X2. Por eso se recomienda O/U 2,5, sabiendo que 1X2 tiene algo más de
evidencia previa de ineficiencia.

## 6. Evaluación honesta de las hipótesis para el mercado recomendado

**H1 (información predictiva adicional):** plausible pero no demostrada.
- El mercado de cierre ya es una referencia exigente: Brier ≈ 0,2406 frente a ≈ 0,2500 de
  la climatología (2019/20-2023/24). El mercado aprovecha poco de la incertidumbre total y
  el margen absoluto de mejora es pequeño.
- Wheatcroft (2020, 2021) sugiere que las estadísticas de tiros y córners contienen
  información adicional. Es una hipótesis concreta y preregistrable.

**H2 (valor esperado positivo con precios reales):** **poco probable para un usuario de
una sola casa**, según la evidencia disponible.
- Wheatcroft (2020): +0,8% por apuesta solo con la cuota **máxima** de todo el mercado
  (margen 1,57%). Con la cuota **promedio** (margen 6,8%) hay pérdida sustancial.
- El margen mediano medido de Bet365 en O/U es 5,8-5,9%, cercano al promedio. El de
  Coolbet es **desconocido** (no hay datos).
- Las casas restringen las cuentas ganadoras (Kaunitz et al. 2017, preprint), algo que
  ningún backtest captura.

**Potencia estadística y laboratorio prospectivo (GATE 5).** Con la tabla del §5, detectar
un ROI del 3% exige ~6.500 apuestas independientes:

| Ritmo de apuestas simuladas | Años para ROI 3% | Años para ROI 5% |
|---|---:|---:|
| 5 por semana | ~25 | ~9 |
| 10 por semana | ~12,5 | ~4,5 |
| 20 por semana | ~6,3 | ~2,3 |

**Consecuencia de diseño:** a escala individual, validar prospectivamente *por ROI* es
inviable en plazos razonables. La validación prospectiva tendrá que basarse en métricas
de mayor potencia: diferencia de log loss contra el mercado, calibración y CLV. Estas
métricas necesitan menos muestra y pueden evaluar *todos* los partidos, no solo los
apostados. Esto debe preregistrarse.

## 7. Alcance propuesto (se congela al aprobar)

| Elemento | Definición |
|---|---|
| Mercado | Over/Under 2,5 goles, tiempo reglamentario (90 min + descuento), dos resultados, sin devolución |
| Competiciones | Las 22 divisiones de Football-Data (E0-E3, EC, SC0-SC3, D1-D2, I1-I2, SP1-SP2, F1-F2, N1, B1, P1, T1, G1), solo partidos de liga incluidos en los archivos |
| Período de desarrollo | 2005/06-2021/22 (pre-cierre Betbrain hasta 2018/19; pre-cierre y cierre multi-casa desde 2019/20) |
| Validación / selección | 2022/23-2023/24 |
| **Prueba final sellada** | **2024/25-2025/26** (y 2026/27 en adelante como prospectivo) |
| Benchmark de mercado | Promedio de cierre y Bet365 de cierre sin margen (Pinnacle excluido desde 23/07/2025) |
| Momento de predicción | Captura pre-cierre (viernes/martes por la tarde), solo con partidos terminados antes |
| Operadores para H2 | Bet365 (una casa), promedio y máximo de mercado. Coolbet solo si se adquieren sus cuotas o se registran prospectivamente |
| Fuera de alcance | Otras líneas (1,5/3,5), 1X2, hándicap asiático, córners, tarjetas, NBA, apuestas en vivo, apuestas reales |

## 8. Criterios que harían abandonar o replantear

Se preregistran ahora, antes de modelar:
1. Si en validación (2022/23-2023/24) ningún modelo mejora la log loss del mercado de
   cierre de forma distinguible del azar (comparación pareada con bootstrap por bloques
   por jornada), **H1 se declara no demostrada** antes de tocar la prueba final.
2. Si la mejora de H1 existe pero no sobrevive al margen de una sola casa (Bet365) en
   validación, **H2 se declara no demostrada** para un usuario de una sola casa.
3. Si GATE 1 revela problemas de integridad o de point-in-time no corregibles, se vuelve a
   GATE 0.

## 9. Decisiones que se solicitan al usuario

1. **¿Aprueba Fútbol O/U 2,5 como mercado único?** Alternativa razonable: 1X2, empatado en
   la matriz. Prefiero O/U 2,5 por potencia estadística y por su compatibilidad con la
   cuota máxima de 3,50.
2. **¿Confirma el sellado de 2024/25-2025/26 como prueba final?**
3. **¿Acepta el universo de 22 divisiones sin selección de ligas?**
4. **¿Desea, más adelante (no ahora), evaluar el gasto en The Odds API** (30-59 USD por un
   mes) para obtener cuotas históricas de Coolbet desde 2020?

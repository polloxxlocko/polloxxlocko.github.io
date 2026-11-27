# RESEARCH_FOUNDATIONS — Fundamentos científicos del proyecto

Versión 1.0 · 2026-11-27 · Fase Cero

## 0. Método de verificación y alcance

Ninguna referencia de este documento se citó de memoria. Cada una pasó por
`phase0/verify_references.py`, que consulta su DOI en Crossref (título, autores, revista,
volumen, páginas) y en OpenAlex o Semantic Scholar (resumen). La salida queda guardada
en `research/references_verified.json` y `research/abstracts_semanticscholar.json`.

**Niveles de verificación** (columna "Nivel" de la bibliografía):

| Nivel | Significado | Qué se puede afirmar |
|---|---|---|
| **T** | Texto completo leído en esta sesión | Detalles metodológicos citados |
| **R** | Resumen oficial leído | Solo lo que dice el resumen |
| **M** | Solo metadatos verificados (resumen no disponible) | Solo el tema que indica el título |

**Incidente registrado:** de 56 DOIs escritos inicialmente de memoria, **5 eran
incorrectos** (resolvían a otros artículos o no existían): Hubáček et al. 2019,
Dixon y Pope 2004, Gandar et al. 1998, Manner 2016 y Dawson et al. 2007. Se corrigieron
mediante búsqueda bibliográfica en Crossref (`EXPERIMENT_LOG.md`, E-000). Esto justifica la
regla de no citar sin verificar.

**Limitación honesta:** solo un estudio (Wheatcroft 2020) se leyó en texto completo.
Para el resto, las afirmaciones se limitan al resumen o al título. No se reproducen
porcentajes de rentabilidad sin indicar muestra, período, mercado y cuotas, y cuando el
resumen no lo dice, se indica.

---

## 1. Modelos de resultados y goles en fútbol

### 1.1 Poisson independiente: Maher (1982) [R]
Incorpora fuerzas ofensiva y defensiva por equipo. Según el resumen, aunque hay
"pequeñas diferencias sistemáticas", un Poisson independiente describe razonablemente
bien los marcadores, a diferencia de autores previos que preferían la binomial negativa.
Es el punto de partida de la especificación de §10.1 del encargo. *Diagnóstico propio
(descriptivo, no prueba de modelo):* en las temporadas no selladas de Football-Data, la
razón varianza/media del total de goles por división-temporada tiene mediana 1,01
(p10 = 0,91; p90 = 1,13). Esto no indica una sobredispersión marginal fuerte.

### 1.2 Dixon y Coles (1997) [R]
Según el resumen: modelo paramétrico basado en regresión de Poisson, ajustado con datos de
liga y copa inglesas de 1992-1995 y evaluado con cuotas de 1995-1996. El modelo muestra
"retorno positivo" como base de una estrategia de apuestas.
- *Muestra y período:* Inglaterra, 1992-1996. Datos de hace 30 años, anteriores al
  mercado online actual.
- *Implicación para O/U 2,5:* la corrección de dependencia actúa sobre 0-0, 1-0, 0-1 y 1-1,
  todos Under 2,5. Con intensidades fijas, su efecto neto sobre P(Under 2,5) se compensa.
  La ponderación temporal sí puede importar. Cualquier mejora debe verificarse
  empíricamente (ver `CLAUDE.md` §4).

### 1.3 Extensiones dinámicas y bivariadas
- **Rue y Salvesen (2000)** [R]: modelo lineal generalizado dinámico bayesiano con
  habilidades de equipo que varían en el tiempo.
- **Karlis y Ntzoufras (2003)** [R]: sustituyen la independencia por un Poisson bivariado
  que permite correlación entre ambos marcadores.
- **Koopman y Lit (2015)** [R]: Poisson bivariado con intensidades que cambian
  estocásticamente (espacio de estados). Validación fuera de muestra en la Premier League
  2010-11 y 2011-12, con "retorno positivo significativo" frente a las cuotas. *Solo dos
  temporadas de una liga.*
- **Koopman y Lit (2019)** [R]: modelo dinámico "score-driven" en seis competiciones
  europeas. El modelo de conteos por pares da los pronósticos más precisos. Incluye
  simulación de apuestas (el resumen no da cifras).
- **Boshnakov, Kharrat y McHale (2017)** [M]: modelo de conteo Weibull bivariado.
- **Baio y Blangiardo (2010)** [R]: modelo bayesiano jerárquico probado en la Serie A
  1991-92. Señalan el problema de sobre-encogimiento (overshrinkage) del modelo jerárquico.
- **Ley, Van de Wiele y Van Eetvelde (2019)** [R]: 10 modelos (Thurstone-Mosteller,
  Bradley-Terry, Poisson independiente y bivariado) estimados por máxima verosimilitud
  ponderada con un **factor de depreciación temporal**. Es un antecedente directo para la
  ponderación temporal.
- **Goddard (2005)** [M]: regresiones para pronosticar goles y resultados.

### 1.4 Modelos asistidos por mercado
- **Egidi, Pauli y Torelli (2018)** [R]: modelo bayesiano jerárquico de Poisson donde las
  tasas de anotación son *combinaciones convexas* de parámetros históricos y de la
  información de las cuotas. Nueve temporadas de ligas europeas para predecir la décima.
  Es un antecedente directo de la línea B (`logit(p) = logit(p_mercado) + f(X)`).
- **Wunderlich y Memmert (2018)** [R]: Elo construido con cuotas. Unos 15.000 partidos
  (2007/08-2016/17, cuatro ligas y competiciones UEFA). Supera al Elo clásico:
  "las cuotas previas contienen más información relevante que el resultado".

## 2. Evidencia específica del mercado Over/Under 2,5

### 2.1 Wheatcroft (2020), *IJF* 36(3) [T, texto completo]
Es el estudio más directamente relevante. Detalles extraídos del manuscrito aceptado
(LSE Research Online, CC BY-NC-ND):

| Aspecto | Detalle |
|---|---|
| Datos | Football-Data.co.uk (la misma fuente auditada aquí) |
| Ligas | 10: Premier League, Championship, League One, League Two, National League, Scottish Premier League, La Liga, Serie A, Ligue 1, Bundesliga |
| Período | Desde 2005/06; "doce años"; 54.437 partidos |
| Modelo | Ratings GAP (rendimiento ofensivo generalizado) → regresión logística → P(Over 2,5) |
| Ajuste | Parámetros del rating optimizados entre temporadas (Nelder-Mead, ignorance score sobre partidos previos); regresión logística reajustada tras cada jornada |
| Entradas probadas | Goles, tiros, tiros a puerta, córners, tiros+córners, tiros a puerta+córners (6 variantes) |
| Cuotas de evaluación | Máximo y promedio Betbrain (columnas `BbMx`/`BbAv`, pre-cierre) |
| Resultado principal | **+0,8% por apuesta** con 68.672 apuestas (apuesta fija, tiros+córners), **suponiendo que siempre se obtuvo la cuota máxima entre todas las casas** (margen medio 1,57%) |
| Con cuota promedio | **Pérdida sustancial** con las dos estrategias (margen medio 6,8%) |
| Robustez | Comparación con apuestas aleatorias de igual frecuencia (1.000.000 de simulaciones). Indica que el pronóstico es *informativo*, pero no corrige la selección entre las 6 variantes |

**Lectura crítica para este proyecto:**
1. La rentabilidad depende de conseguir siempre el mejor precio del mercado. Un usuario
   que opera con una sola casa (Coolbet) no tiene ese precio. Con precios promedio, el
   mismo modelo pierde.
2. La variante destacada (tiros+córners) se eligió entre 6 tras observar los resultados:
   hay riesgo de selección múltiple.
3. El resultado sugiere que las estadísticas de tiros contienen información adicional
   sobre los goles. Esta hipótesis es concreta y verificable (y debe preregistrarse).
4. Para H2 importa el margen efectivo de la casa usada. Este proyecto midió un margen
   mediano de cierre O/U de 5,8-5,9% en Bet365 desde 2019/20 (`DATA_FEASIBILITY_REPORT.md`).

### 2.2 Wheatcroft (2021), *J. Sports Analytics* 7(2) [R]
Las estadísticas del partido *predichas* antes del encuentro (ratings GAP y "Bivariate
Attacking") aportan información "más allá de la reflejada en las cuotas". El autor
informa de un beneficio "a largo plazo y robusto". El resumen no da cuotas ni cifras.

### 2.3 Lo que no se encontró
No se encontró una replicación independiente revisada por pares de una ventaja en
O/U 2,5. **Evidencia de ineficiencia en O/U 2,5: limitada a una línea de investigación.**

## 3. Ratings, regresión logística, xG y machine learning

- **Hvattum y Arntzen (2010)** [M]: Elo para predecir resultados en fútbol.
- **Lasek, Szlávik y Bhulai (2013)** [R]: comparación de sistemas de ranking (benchmark: ranking FIFA de selecciones); una versión de Elo es la de mejor desempeño.
- **Expected Goals: Mead, O'Hare y McMenemy (2023)** [R]: mejora de modelos xG con
  aprendizaje automático. *Advertencia de datos:* no se encontró xG histórico gratuito,
  legal y accesible desde este entorno (ver `DATA_FEASIBILITY_REPORT.md`). El xG queda
  fuera de la línea base.
- **Hubáček, Šourek y Železný (2019)** [R]: sistema de ML que también *reduce la
  correlación con las predicciones de la casa*, usa redes convolucionales y asigna las
  apuestas como cartera. Beneficios acumulados positivos en NBA 2007-2014.
- **Walsh y Joshi (2024)** [R]: en NBA, seleccionar modelos por calibración en vez de
  precisión da mayores retornos (ROI +34,69% frente a -35,17%) en *una sola temporada*.
  Cifras extremas sobre una sola temporada: **baja credibilidad como estimación de
  rentabilidad**. La conclusión metodológica (calibración > precisión) sí es relevante.
- **Revisiones:** Bunker y Susnjak (2022) [R], estudios de ML en deportes de equipo de
  1996 a 2019; Horvat y Job (2020) [R].

## 4. Eficiencia de los mercados de apuestas

| Estudio | Nivel | Lo verificado |
|---|:---:|---|
| Kuypers (2000) | R | Mercado de cuota fija inglés: una casa que maximiza beneficio puede fijar cuotas ineficientes; evidencia de ineficiencia con oportunidades rentables (datos de hace más de 25 años) |
| Cain, Law y Peel (2000) | R | Sesgo favorito-longshot en el fútbol británico (resultados y marcadores exactos) |
| Forrest, Goddard y Simmons (2005) | R | ~10.000 partidos ingleses: las cuotas son cada vez más eficaces en 5 años; el modelo estadístico no supera a las casas |
| Dixon y Pope (2004) | M | Valor de los pronósticos estadísticos en el mercado británico |
| Spann y Skiera (2009) | R | 678-837 partidos de tres temporadas de la Bundesliga: mercados de predicción y cuotas tienen precisión similar y ambos superan ampliamente a los tipsters |
| Levitt (2004) | R | Las casas no actúan como creadores de mercado: fijan precios, toman posiciones y son más hábiles pronosticando que los apostadores |
| Snowberg y Wolfers (2010) | R | Sesgo favorito-longshot en carreras de caballos: contrasta amor al riesgo frente a percepción errónea de probabilidades |
| Angelini y De Angelis (2019) | R | 41 casas, 11 ligas europeas, 11 años: con mejores cuotas, 8 mercados eficientes y 3 con ineficiencias explotables (1X2) |
| Constantinou, Fenton y Neil (2013) | R | Red bayesiana; pronósticos publicados antes de cada partido de la EPL 2011/12; rentable frente a cuotas publicadas (una temporada) |
| Kaunitz, Zhong y Kreiner (2017) | Preprint arXiv 1710.02824, **no revisado por pares** | Estrategia que usa el consenso de cuotas para detectar precios desalineados; rentable en 10 años de cierre y 5 meses con dinero real; las casas respondieron con "prácticas discriminatorias" (limitación de cuentas) |

**Síntesis:** la evidencia es mixta. Los resultados positivos suelen depender de (a) datos
antiguos, (b) una o dos temporadas, (c) mejores cuotas entre muchas casas o (d) ausencia de
corrección por pruebas múltiples. Hay evidencia directa (Forrest et al. 2005) de que las
casas mejoraron como pronosticadoras. Además, Kaunitz et al. documentan **limitaciones de
ejecución**: una ventaja demostrable puede no ser explotable porque las casas restringen
las cuentas ganadoras.

**NBA y totales:**
- Gandar et al. (1998) [R]: en el mercado de spread NBA, los movimientos de línea de
  apertura a cierre mejoran significativamente la precisión y eliminan sesgos de la apertura.
- Gandar et al. (2000) [R]: en totales NBA, **las líneas de cierre son pronósticos más
  precisos que las de apertura**, y los movimientos van en la dirección correcta.
- Manner (2016) [R]: ocho temporadas NBA; evidencia débil de heterocedasticidad; fuerzas
  de equipo dinámicas en espacio de estados.
- "Player absence and betting lines in the NBA" (2015) [M].
- Paul y Weinbach (2002) [R]: **NFL** (no NBA), totales 1979-2000. El Under gana más del 50%
  de las veces, pero no se rechaza la hipótesis de apuesta justa.

**No se encontraron estudios revisados por pares sobre la eficiencia de los props
individuales de NBA.**

**Córners y tarjetas:** Dawson et al. (2007) [R] analizan la incidencia de tarjetas en la
Premier League 1996-2003 y apoyan la consistencia temporal de la tasa media de sanciones.
Boyko et al. (2007) [R] muestran que los árbitros difieren en su sesgo de localía. Ambos
estudian el *arbitraje*, no el *mercado*. **No se encontraron estudios revisados por pares
sobre la eficiencia de los mercados de córners o tarjetas.** (Ausencia de evidencia, no
evidencia de ausencia.)

## 5. Eliminación del margen

- **Shin (1991, 1993)** [R]: con apostadores informados (insiders), las cuotas
  normalizadas se desvían sistemáticamente de las probabilidades verdaderas ("regla de la
  raíz cuadrada"). Es la base del "método de Shin".
- **Štrumbelj (2014)** [M]: determinación de probabilidades a partir de cuotas.
- **Clarke, Kovalchik e Ingram (2017)** [R]: el método aditivo puede dar probabilidades
  negativas y la normalización no recoge el sesgo favorito-longshot. **Shin y el método
  aditivo son equivalentes con dos competidores.** El método de potencia supera
  universalmente al multiplicativo y supera o iguala a Shin en tres conjuntos de datos.
- *Implicación:* en O/U (dos resultados) se comparan, con datos fuera de muestra,
  normalización proporcional y método de potencia. Shin no aporta nada distinto del aditivo.

## 6. Evaluación probabilística y calibración

- **Brier (1950)** [M] y **Murphy (1973)** [R]: el Brier score y su descomposición
  (fiabilidad, resolución, incertidumbre). El Brier mezcla calibración y discriminación:
  hay que evaluarlas por separado.
- **Gneiting y Raftery (2007)** [R]: reglas de puntuación estrictamente propias.
- **Constantinou y Fenton (2012)** [R] proponen el RPS para 1X2 por su carácter ordinal.
  **Wheatcroft (2021, JQAS)** [R] argumenta en su contra. Para O/U (binario) basta con log
  loss y Brier.
- **Cox (1958)** [M]: dos aplicaciones de la regresión binaria. Se cita habitualmente como origen de la pendiente/intercepto de calibración (contenido no verificado en esta sesión).
  **Van Calster et al. (2019)** [R]: la calibración es el "talón de Aquiles" de la analítica
  predictiva.
- **Zadrozny y Elkan (2002)** [R], calibración multiclase a partir de calibradores binarios. **Niculescu-Mizil y Caruana
  (2005)** [R], comparación de Platt e isotónica. (Platt 1999 es un capítulo de libro sin
  DOI verificado en esta sesión: no se cita como verificado.)

## 7. Backtesting, incertidumbre y selección múltiple

- **Diebold y Mariano (1995)** [R]: comparación de precisión predictiva entre pronósticos.
- **Künsch (1989)** [R] y **Politis y Romano (1994)** [R]: bootstrap por bloques y
  estacionario para datos dependientes.
- **White (2000)** [R] (Reality Check) y **Hansen (2005)** [R] (SPA): data snooping al
  comparar muchas variantes contra un benchmark.
- **Benjamini y Hochberg (1995)** [R]: control de la tasa de falsos descubrimientos.
- **Bailey et al. (2016/2017)** [R]: probabilidad de sobreajuste del backtest (PBO). Los
  hold-out estándar son poco fiables en backtests de estrategias.
  **Bailey y López de Prado (2014)** [R]: Sharpe deflactado. **Harvey y Liu (2015)** [R]:
  "haircut" del rendimiento por pruebas múltiples.

## 8. Closing Line Value (CLV)

No se encontró una fuente revisada por pares que formalice el CLV como métrica de
validación. El concepto viene sobre todo de la literatura práctica. Hay evidencia
relacionada: Gandar et al. (1998, 2000) muestran en la NBA que las líneas de cierre son
más precisas que las de apertura, lo que es consistente con que el cierre incorpore
información. Kaunitz et al. (2017, preprint) usan cuotas de cierre como referencia. En este
proyecto el CLV será un
**indicador complementario**, nunca prueba suficiente de ventaja. Ventaja estadística: su
varianza es mucho menor que la del ROI, así que puede dar señal con muestras pequeñas.
Esto debe verificarse empíricamente con los datos de cierre disponibles.

## 9. Limitaciones de la evidencia disponible

1. **Sesgo de publicación:** los estudios con resultados rentables tienen más probabilidad
   de publicarse.
2. **Supuesto de mejor precio:** varios resultados positivos usan cuotas máximas entre
   decenas de casas, inalcanzables para un usuario de una sola casa.
3. **Muestras cortas:** muchos estudios cubren 1-2 temporadas.
4. **Selección de variantes:** pocas aplican controles de pruebas múltiples.
5. **Antigüedad:** gran parte de la evidencia de ineficiencia es de 1995-2015. El mercado
   online cambió desde entonces y Forrest et al. (2005) ya documentan mejoras de las casas.
6. **Ejecución:** la limitación de cuentas (Kaunitz et al.) no aparece en los backtests.
7. **Cobertura de esta revisión:** basada en metadatos y resúmenes. Solo un texto completo.

## 10. Implicaciones para el diseño

1. El benchmark es el **mercado sin margen**, no la climatología ni el % de aciertos.
2. H1 (predictiva) se evalúa primero con reglas propias y comparación pareada contra el
   mercado. H2 (económica) solo con precios reales del operador usado.
3. Para O/U se prueban, como hipótesis preregistradas: (a) Poisson con ponderación
   temporal, (b) entradas de tiros (Wheatcroft) y (c) modelo asistido por mercado (Egidi
   et al.; Wunderlich y Memmert).
4. Las comparaciones múltiples se controlan (BH, Reality Check/SPA) y todas las variantes
   se registran.
5. Se reporta la sensibilidad al operador: Bet365 (una casa), promedio y máximo del
   mercado, y Coolbet si se adquieren sus cuotas.

---

## Bibliografía verificada

Generada automáticamente desde `research/references_verified.json`. Kaunitz et al. (2017)
es un preprint de arXiv (id 1710.02824, verificado vía API de arXiv), sin DOI de revista.

| Clave | Referencia (metadatos de Crossref) | DOI | Nivel |
|---|---|---|:---:|
| `angelini2019` | Angelini, De Angelis (2019). Efficiency of online football betting markets. *International Journal of Forecasting* 35(2):712-721 | [10.1016/j.ijforecast.2018.07.008](https://doi.org/10.1016/j.ijforecast.2018.07.008) | R |
| `bailey_lopezdeprado2014_dsr` | Bailey, López de Prado (2014). The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality. *The Journal of Portfolio Management* 40(5):94-107 | [10.3905/jpm.2014.40.5.094](https://doi.org/10.3905/jpm.2014.40.5.094) | R |
| `bailey2017_pbo` | Bailey, Borwein, López de Prado et al. (2016). The probability of backtest overfitting. *The Journal of Computational Finance*  | [10.21314/JCF.2016.322](https://doi.org/10.21314/JCF.2016.322) | R |
| `baio_blangiardo2010` | Baio, Blangiardo (2010). Bayesian hierarchical model for the prediction of football results. *Journal of Applied Statistics* 37(2):253-264 | [10.1080/02664760802684177](https://doi.org/10.1080/02664760802684177) | R |
| `benjamini_hochberg1995` | Benjamini, Hochberg (1995). Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing. *Journal of the Royal Statistical Society Series B: Statistical Methodology* 57(1):289-300 | [10.1111/j.2517-6161.1995.tb02031.x](https://doi.org/10.1111/j.2517-6161.1995.tb02031.x) | R |
| `boshnakov2017` | Boshnakov, Kharrat, McHale (2017). A bivariate Weibull count model for forecasting association football scores. *International Journal of Forecasting* 33(2):458-466 | [10.1016/j.ijforecast.2016.11.006](https://doi.org/10.1016/j.ijforecast.2016.11.006) | M |
| `boyko2007` | Boyko, Boyko, Boyko (2007). Referee bias contributes to home advantage in English Premiership football. *Journal of Sports Sciences* 25(11):1185-1194 | [10.1080/02640410601038576](https://doi.org/10.1080/02640410601038576) | R |
| `brier1950` | BRIER (1950). VERIFICATION OF FORECASTS EXPRESSED IN TERMS OF PROBABILITY. *Monthly Weather Review* 78(1):1-3 | [10.1175/1520-0493(1950)078&lt;0001:VOFEIT&gt;2.0.CO;2](https://doi.org/10.1175/1520-0493(1950)078%3C0001:VOFEIT%3E2.0.CO;2) | M |
| `bunker_susnjak2022` | Bunker, Susnjak (2022). The Application of Machine Learning Techniques for Predicting Match Results in Team Sport: A Review. *Journal of Artificial Intelligence Research* 73:1285-1322 | [10.1613/jair.1.13509](https://doi.org/10.1613/jair.1.13509) | R |
| `cain2000` | Cain, Law, Peel (2000). The Favourite‐Longshot Bias and Market Efficiency in UK Football betting. *Scottish Journal of Political Economy* 47(1):25-36 | [10.1111/1467-9485.00151](https://doi.org/10.1111/1467-9485.00151) | R |
| `clarke2017` | Clarke, Kovalchik, Ingram (2017). Adjusting Bookmaker’s Odds to Allow for Overround. *American Journal of Sports Science* 5(6):45-49 | [10.11648/j.ajss.20170506.12](https://doi.org/10.11648/j.ajss.20170506.12) | R |
| `constantinou_fenton2012` | Constantinou, Fenton (2012). Solving the Problem of Inadequate Scoring Rules for Assessing Probabilistic Football Forecast Models. *Journal of Quantitative Analysis in Sports* 8(1) | [10.1515/1559-0410.1418](https://doi.org/10.1515/1559-0410.1418) | R |
| `constantinou2013` | Constantinou, Fenton, Neil (2013). Profiting from an inefficient association football gambling market: Prediction, risk and uncertainty using Bayesian networks. *Knowledge-Based Systems* 50:60-86 | [10.1016/j.knosys.2013.05.008](https://doi.org/10.1016/j.knosys.2013.05.008) | R |
| `cox1958` | COX (1958). Two further applications of a model for binary regression. *Biometrika* 45(3-4):562-565 | [10.1093/biomet/45.3-4.562](https://doi.org/10.1093/biomet/45.3-4.562) | M |
| `nba_player_absence2015` | Dare, Dennis, Paul (2015). Player absence and betting lines in the NBA. *Finance Research Letters* 13:130-136 | [10.1016/j.frl.2015.02.004](https://doi.org/10.1016/j.frl.2015.02.004) | M |
| `dawson2007` | Dawson, Dobson, Goddard et al. (2007). Are Football Referees Really Biased and Inconsistent?: Evidence on the Incidence of Disciplinary Sanction in the English Premier League. *Journal of the Royal Statistical Society Series A: Statistics in Society* 170(1):231-250 | [10.1111/j.1467-985x.2006.00451.x](https://doi.org/10.1111/j.1467-985x.2006.00451.x) | R |
| `diebold_mariano1995` | Diebold, Mariano (1995). Comparing Predictive Accuracy. *Journal of Business &amp; Economic Statistics* 13(3):253-263 | [10.1080/07350015.1995.10524599](https://doi.org/10.1080/07350015.1995.10524599) | R |
| `dixon_coles1997` | Dixon, Coles (1997). Modelling Association Football Scores and Inefficiencies in the Football Betting Market. *Journal of the Royal Statistical Society Series C: Applied Statistics* 46(2):265-280 | [10.1111/1467-9876.00065](https://doi.org/10.1111/1467-9876.00065) | R |
| `dixon_pope2004` | Dixon, Pope (2004). The value of statistical forecasts in the UK association football betting market. *International Journal of Forecasting* 20(4):697-711 | [10.1016/j.ijforecast.2003.12.007](https://doi.org/10.1016/j.ijforecast.2003.12.007) | M |
| `egidi2018` | Egidi, Pauli, Torelli (2018). Combining historical data and bookmakers’ odds in modelling football scores. *Statistical Modelling* 18(5-6):436-459 | [10.1177/1471082X18798414](https://doi.org/10.1177/1471082X18798414) | R |
| `forrest2005` | Forrest, Goddard, Simmons (2005). Odds-setters as forecasters: The case of English football. *International Journal of Forecasting* 21(3):551-564 | [10.1016/j.ijforecast.2005.03.003](https://doi.org/10.1016/j.ijforecast.2005.03.003) | R |
| `gandar1998_nba` | Gandar, Dare, Brown et al. (1998). Informed Traders and Price Variations in the Betting Market for Professional Basketball Games. *The Journal of Finance* 53(1):385-401 | [10.1111/0022-1082.155346](https://doi.org/10.1111/0022-1082.155346) | R |
| `gandar2000_nba_totals` | Gandar, Zuber, Dare (2000). The Search for Informed Traders in the Totals Betting Market for National Basketball Association Games. *Journal of Sports Economics* 1(2):177-186 | [10.1177/152700250000100205](https://doi.org/10.1177/152700250000100205) | R |
| `gneiting_raftery2007` | Gneiting, Raftery (2007). Strictly Proper Scoring Rules, Prediction, and Estimation. *Journal of the American Statistical Association* 102(477):359-378 | [10.1198/016214506000001437](https://doi.org/10.1198/016214506000001437) | R |
| `goddard2005` | Goddard (2005). Regression models for forecasting goals and match results in association football. *International Journal of Forecasting* 21(2):331-340 | [10.1016/j.ijforecast.2004.08.002](https://doi.org/10.1016/j.ijforecast.2004.08.002) | M |
| `hansen2005` | Hansen (2005). A Test for Superior Predictive Ability. *Journal of Business &amp; Economic Statistics* 23(4):365-380 | [10.1198/073500105000000063](https://doi.org/10.1198/073500105000000063) | R |
| `harvey_liu2015` | Harvey, Liu (2015). Backtesting. *The Journal of Portfolio Management* 42(1):13-28 | [10.3905/jpm.2015.42.1.013](https://doi.org/10.3905/jpm.2015.42.1.013) | R |
| `horvat_job2020` | Horvat, Job (2020). The use of machine learning in sport outcome prediction: A review. *WIREs Data Mining and Knowledge Discovery* 10(5) | [10.1002/widm.1380](https://doi.org/10.1002/widm.1380) | R |
| `hubacek2019` | Hubáček, Šourek, Železný (2019). Exploiting sports-betting market using machine learning. *International Journal of Forecasting* 35(2):783-796 | [10.1016/j.ijforecast.2019.01.001](https://doi.org/10.1016/j.ijforecast.2019.01.001) | R |
| `hvattum_arntzen2010` | Hvattum, Arntzen (2010). Using ELO ratings for match result prediction in association football. *International Journal of Forecasting* 26(3):460-470 | [10.1016/j.ijforecast.2009.10.002](https://doi.org/10.1016/j.ijforecast.2009.10.002) | M |
| `karlis_ntzoufras2003` | Karlis, Ntzoufras (2003). Analysis of sports data by using bivariate Poisson models. *Journal of the Royal Statistical Society: Series D (The Statistician)* 52(3):381-393 | [10.1111/1467-9884.00366](https://doi.org/10.1111/1467-9884.00366) | R |
| `koopman_lit2015` | Koopman, Lit (2015). A Dynamic Bivariate Poisson Model for Analysing and Forecasting Match Results in the English Premier League. *Journal of the Royal Statistical Society Series A: Statistics in Society* 178(1):167-186 | [10.1111/rssa.12042](https://doi.org/10.1111/rssa.12042) | R |
| `koopman_lit2019` | Koopman, Lit (2019). Forecasting football match results in national league competitions using score-driven time series models. *International Journal of Forecasting* 35(2):797-809 | [10.1016/j.ijforecast.2018.10.011](https://doi.org/10.1016/j.ijforecast.2018.10.011) | R |
| `kunsch1989` | Kunsch (1989). The Jackknife and the Bootstrap for General Stationary Observations. *The Annals of Statistics* 17(3):1217-1241 | [10.1214/aos/1176347265](https://doi.org/10.1214/aos/1176347265) | R |
| `kuypers2000` | Kuypers (2000). Information and efficiency: an empirical study of a fixed odds betting market. *Applied Economics* 32(11):1353-1363 | [10.1080/00036840050151449](https://doi.org/10.1080/00036840050151449) | R |
| `lasek2013` | Lasek, Szlávik, Bhulai (2013). The predictive power of ranking systems in association football. *International Journal of Applied Pattern Recognition* 1(1):27 | [10.1504/IJAPR.2013.052339](https://doi.org/10.1504/IJAPR.2013.052339) | R |
| `levitt2004` | Levitt (2004). Why are Gambling Markets Organised so Differently from Financial Markets?. *The Economic Journal* 114(495):223-246 | [10.1111/j.1468-0297.2004.00207.x](https://doi.org/10.1111/j.1468-0297.2004.00207.x) | R |
| `ley2019` | Ley, Wiele, Eetvelde (2019). Ranking soccer teams on the basis of their current strength: A comparison of maximum likelihood approaches. *Statistical Modelling* 19(1):55-73 | [10.1177/1471082X18817650](https://doi.org/10.1177/1471082X18817650) | R |
| `maher1982` | Maher (1982). Modelling association football scores. *Statistica Neerlandica* 36(3):109-118 | [10.1111/j.1467-9574.1982.tb00782.x](https://doi.org/10.1111/j.1467-9574.1982.tb00782.x) | R |
| `manner2016_nba` | Manner (2016). Modeling and forecasting the outcomes of NBA basketball games. *Journal of Quantitative Analysis in Sports* 12(1):31-41 | [10.1515/jqas-2015-0088](https://doi.org/10.1515/jqas-2015-0088) | R |
| `mead2023_xg` | Mead, O’Hare, McMenemy (2023). Expected goals in football: Improving model performance and demonstrating value. *PLOS ONE* 18(4):e0282295 | [10.1371/journal.pone.0282295](https://doi.org/10.1371/journal.pone.0282295) | R |
| `murphy1973` | Murphy (1973). A New Vector Partition of the Probability Score. *Journal of Applied Meteorology* 12(4):595-600 | [10.1175/1520-0450(1973)012&lt;0595:ANVPOT&gt;2.0.CO;2](https://doi.org/10.1175/1520-0450(1973)012%3C0595:ANVPOT%3E2.0.CO;2) | R |
| `niculescu_caruana2005` | Niculescu-Mizil, Caruana (2005). Predicting good probabilities with supervised learning. *Proceedings of the 22nd international conference on Machine learning  - ICML '05* :625-632 | [10.1145/1102351.1102430](https://doi.org/10.1145/1102351.1102430) | R |
| `paul_weinbach2002_totals` | Paul, Weinbach (2002). Market Efficiency and a Profitable Betting Rule. *Journal of Sports Economics* 3(3):256-263 | [10.1177/1527002502003003003](https://doi.org/10.1177/1527002502003003003) | R |
| `politis_romano1994` | Politis, Romano (1994). The Stationary Bootstrap. *Journal of the American Statistical Association* 89(428):1303-1313 | [10.1080/01621459.1994.10476870](https://doi.org/10.1080/01621459.1994.10476870) | R |
| `rue_salvesen2000` | Rue, Salvesen (2000). Prediction and Retrospective Analysis of Soccer Matches in a League. *Journal of the Royal Statistical Society: Series D (The Statistician)* 49(3):399-418 | [10.1111/1467-9884.00243](https://doi.org/10.1111/1467-9884.00243) | R |
| `shin1991` | Shin (1991). Optimal Betting Odds Against Insider Traders. *The Economic Journal* 101(408):1179 | [10.2307/2234434](https://doi.org/10.2307/2234434) | R |
| `shin1993` | Shin (1993). Measuring the Incidence of Insider Trading in a Market for State-Contingent Claims. *The Economic Journal* 103(420):1141 | [10.2307/2234240](https://doi.org/10.2307/2234240) | R |
| `snowberg_wolfers2010` | Snowberg, Wolfers (2010). Explaining the Favorite–Long Shot Bias: Is it Risk-Love or Misperceptions?. *Journal of Political Economy* 118(4):723-746 | [10.1086/655844](https://doi.org/10.1086/655844) | R |
| `spann_skiera2009` | Spann, Skiera (2009). Sports forecasting: a comparison of the forecast accuracy of prediction markets, betting odds and tipsters. *Journal of Forecasting* 28(1):55-72 | [10.1002/for.1091](https://doi.org/10.1002/for.1091) | R |
| `vancalster2019` | Van Calster, McLernon, van Smeden et al. (2019). Calibration: the Achilles heel of predictive analytics. *BMC Medicine* 17(1) | [10.1186/s12916-019-1466-7](https://doi.org/10.1186/s12916-019-1466-7) | R |
| `walsh_joshi2024` | Walsh, Joshi (2024). Machine learning for sports betting: Should model selection be based on accuracy or calibration?. *Machine Learning with Applications* 16:100539 | [10.1016/j.mlwa.2024.100539](https://doi.org/10.1016/j.mlwa.2024.100539) | R |
| `wheatcroft2020_ou` | Wheatcroft (2020). A profitable model for predicting the over/under market in football. *International Journal of Forecasting* 36(3):916-932 | [10.1016/j.ijforecast.2019.11.001](https://doi.org/10.1016/j.ijforecast.2019.11.001) | T |
| `wheatcroft2021_rps` | Wheatcroft (2021). Evaluating probabilistic forecasts of football matches: the case against the ranked probability score. *Journal of Quantitative Analysis in Sports* 17(4):273-287 | [10.1515/jqas-2019-0089](https://doi.org/10.1515/jqas-2019-0089) | R |
| `wheatcroft2021_stats` | Wheatcroft (2021). Forecasting football matches by predicting match statistics. *Journal of Sports Analytics* 7(2):77-97 | [10.3233/JSA-200462](https://doi.org/10.3233/JSA-200462) | R |
| `white2000` | White (2000). A Reality Check for Data Snooping. *Econometrica* 68(5):1097-1126 | [10.1111/1468-0262.00152](https://doi.org/10.1111/1468-0262.00152) | R |
| `wunderlich_memmert2018` | Wunderlich, Memmert (2018). The Betting Odds Rating System: Using soccer forecasts to forecast soccer. *PLOS ONE* 13(6):e0198668 | [10.1371/journal.pone.0198668](https://doi.org/10.1371/journal.pone.0198668) | R |
| `zadrozny_elkan2002` | Zadrozny, Elkan (2002). Transforming classifier scores into accurate multiclass probability estimates. *Proceedings of the eighth ACM SIGKDD international conference on Knowledge discovery and data mining* :694-699 | [10.1145/775047.775151](https://doi.org/10.1145/775047.775151) | R |
| `strumbelj2014` | Štrumbelj (2014). On determining probability forecasts from betting odds. *International Journal of Forecasting* 30(4):934-943 | [10.1016/j.ijforecast.2014.02.008](https://doi.org/10.1016/j.ijforecast.2014.02.008) | M |

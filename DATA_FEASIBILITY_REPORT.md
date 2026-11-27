# DATA_FEASIBILITY_REPORT — Auditoría de fuentes de datos

Versión 1.0 · 2026-11-27 · Fase Cero

Todas las afirmaciones de este informe provienen de **peticiones reales hechas en esta
sesión** (2026-11-27) desde un contenedor cloud. Cuando una fuente no respondió, se indica.
Que algo no sea accesible desde este entorno **no** prueba que tampoco lo sea desde un
equipo doméstico.

Reproducción:
```bash
python phase0/download_football_data.py --first 0001 --last 2627
python phase0/audit_football_data.py
python phase0/market_selection.py
```
Salidas en `reports/phase0/` y manifiesto RAW en `data/raw/football_data/manifest.jsonl`
(URL, fecha UTC de descarga y SHA-256 de cada archivo).

---

## 1. Resumen ejecutivo

| Fuente | Accesible aquí | Coste | Utilidad | Veredicto |
|---|---|---|---|---|
| **Football-Data.co.uk** | Sí (descargada completa) | Gratis | Resultados, estadísticas y cuotas 1X2/O/U 2,5/AH pre-cierre y cierre | **Fuente principal viable** |
| The Odds API | Sí (docs); API requiere clave | Gratis 500 créditos/mes; históricos desde 30 USD/mes | Snapshots históricos (5-10 min) desde jun-2020; **incluye Coolbet** | Complemento opcional de pago |
| SportsbookReviewsOnline (NBA) | Sí | Gratis | Moneyline y líneas NBA 2007-08 a 2022-23 | Desactualizado; sin precio de totales |
| StatsBomb Open Data | Sí | Gratis (licencia propia) | Eventos de 80 competición-temporadas, sin cuotas | Insuficiente para un mercado de liga |
| Understat | **No** (página de error/bloqueo) | — | xG ligas top | No verificado; no eludir |
| FBref | **No** (desafío anti-bot, 403) | — | Perdió xG/Opta en ene-2026 según fuentes secundarias | No usar |
| Basketball-Reference | Sí | Gratis | Box scores NBA | **Términos prohíben uso para ML predictivo** |
| stats.nba.com | **No** (timeout) | — | Estadísticas oficiales NBA | Bloqueo de IPs cloud documentado por la comunidad |
| Coolbet (web) | Solo shell de la SPA | — | Cuotas actuales | Sin archivo histórico público |
| AusSportsBetting (NBA) | **No** (403) | — | — | No verificado |
| Kaggle | Requiere cuenta | — | Datasets de terceros | Procedencia/licencia no verificadas |

## 2. Football-Data.co.uk (fuente principal)

### 2.1 Condiciones de acceso y licencia
- La página de descargas dice textualmente: *"My data is free"*. Los datos se publican para
  "quantitative testing of betting systems". El sitio se financia con publicidad de casas
  de apuestas (divulgación de afiliados en la portada).
- No se encontró una licencia formal (CC u otra). **Supuesto de trabajo:** uso privado y
  de investigación, con atribución. No redistribuir los CSV.
- Fuentes reconocidas en `notes.txt`: XScores (resultados), BBC/Flashscore/ESPN y otras
  (estadísticas), Betbrain/Oddsportal y casas individuales (cuotas).

### 2.2 Descarga
- 27 archivos `data.zip` (2000/01 a 2026/27), 17 MB, 589 archivos división-temporada.
- **200.825 partidos** con resultado en 22 divisiones de 11 países (E0-E3, EC, SC0-SC3,
  D1-D2, I1-I2, SP1-SP2, F1-F2, N1, B1, P1, T1, G1).
- 2026/27 está **en curso** (2.680 partidos a la fecha de descarga).

### 2.3 Momento de disponibilidad de las cuotas (point-in-time)
Texto verificado en `data.php` y `notes.txt`:
- Cuotas **pre-cierre**: "collected Friday afternoons for weekend fixtures, and on Tuesday
  afternoons for midweek games". Desde 2019/20 se captura "after market opening at times
  specified on my fixtures page".
- Cuotas de **cierre** (sufijo `C`): desde 2019/20. Cierre 1X2 de Pinnacle desde 2012/13.
- Hora de inicio (`Time`): desde 2019/20.
- *Implicación:* la predicción histórica debe simularse en el momento de captura
  pre-cierre (viernes/martes) usando solo partidos ya terminados. La fecha exacta de
  captura no viene por fila; se infiere de la regla publicada. **Limitación.**

### 2.4 Cobertura medida (proporción de partidos con el dato)

| Temporadas | 1X2 pre | O/U pre | O/U cierre | Córners | Tarjetas | Árbitro | Tiros a puerta | xG | Hora |
|---|---|---|---|---|---|---|---|---|---|
| 2000/01-2001/02 | 0% | 0% | 0% | ~47% | ~48% | ~48% | ~47% | 0% | 0% |
| 2002/03-2004/05 | 93-97% (B365) | 16-26% (B365) | 0% | ~33% | ~33% | ~31% | ~31% | 0% | 0% |
| 2005/06-2016/17 | ~100% | ~100% (prom./máx. Betbrain) | 0% | 47-58% | 54-58% | 36-41% | 47-58% | 0% | 0% |
| 2017/18-2018/19 | ~100% | ~100% (Betbrain) | 0% | 93% | 100% | 43-44% | 93% | 0% | 0% |
| 2019/20-2024/25 | ~100% | ~100% (B365, Pinnacle, prom., máx.) | ~100% (B365C, PC, AvgC, MaxC) | 93-94% | 100% | 40-44% | 93-94% | 0% | 100% |
| 2025/26 | ~100% | ~100% (Pinnacle 38%) | ~100% (Pinnacle 39%) | 93% | 100% | 44% | 93% | 0% | 100% |
| 2026/27 (en curso) | 100% | 100% (Pinnacle 0%) | 100% (Pinnacle 0%) | 100% | 100% | 45% | 100% | 83% | 100% |

Detalle por temporada y división: `reports/phase0/football_data_coverage_by_season.csv` y
`..._by_season_div.csv`.

Hallazgos:
- **O/U 2,5 cierre:** 55.943 partidos con Bet365 y promedio de cierre (2019/20-2026/27).
  ~169.400 partidos con alguna cuota O/U pre-cierre (2002/03 en adelante).
- **Córners y tarjetas:** las estadísticas existen (93-100% desde 2017/18; antes, solo en
  10 divisiones: D1, E0-E3, EC, F1, I1, SC0, SP1). **No hay ninguna cuota de córners ni
  de tarjetas.** La National League (EC) casi no tiene córners desde 2019/20 (5,8%).
- **Árbitro:** solo divisiones inglesas y escocesas (0% en las demás). Para tarjetas, el
  efecto árbitro no se puede modelar en 13 de 22 divisiones.
- **Tarjetas, definiciones:** según `notes.txt`, en Inglaterra/Escocia la amarilla previa a
  una roja por doble amonestación no se cuenta, y en Europa sí. Puede no coincidir con
  las reglas de liquidación de las casas.
- **xG:** columnas `HxG/AxG` presentes **solo en 2026/27**. **No hay xG histórico** en
  esta fuente.

### 2.5 Márgenes medidos (overround mediano, mercados completos, 2019/20+)

| Mercado / fuente | Pre-cierre | Cierre |
|---|---:|---:|
| O/U 2,5 — Bet365 | 5,9% | 5,9% |
| O/U 2,5 — promedio de mercado | 6,2% | 6,2% |
| O/U 2,5 — Pinnacle | 3,9% | 3,4% |
| O/U 2,5 — máximo de mercado | 2,4% | 1,5% |
| 1X2 — Bet365 | 6,5% | 6,5% |
| 1X2 — promedio de mercado | 6,7% | 6,5% |
| 1X2 — Pinnacle | 3,8% | 3,4% |

El margen del "máximo de mercado" combina las mejores cuotas de casas distintas: un
apostador de una sola casa no lo obtiene.

### 2.6 Integridad (resultados de `audit_football_data.py`)

| Prueba | Resultado | Acción |
|---|---|---|
| Filas con más campos que la cabecera | 8.038 (solo 2001/02-2009/10) | Recuperadas rellenando la cabecera (los campos iniciales están alineados). Corregir en la ingesta de GATE 1 |
| Alias de columnas `HT/AT` (Grecia 2000/01-2004/05) | Producía 755 falsos duplicados | Normalizado; **0 duplicados reales** |
| Cuotas < 1,01 | 10 valores | Marcar como inválidos en GATE 1 |
| `FTR` incoherente con el marcador | 0 | — |
| Fechas no parseables | 0 | Formatos `dd/mm/yy` y `dd/mm/yyyy` |
| Encabezados con nombres repetidos | Presentes en algunos archivos | Se desambiguan con sufijo |

### 2.7 Advertencia crítica: Pinnacle desde el 23/07/2025
`data.php` dice textualmente que la API pública de Pinnacle "has become unreliable meaning
their odds are systematically out of date", y que se excluyó de promedios y máximos.
**Verificación empírica propia** (solo cuotas): diferencia absoluta entre P(Over) justa de
Pinnacle y de Bet365:

| Tipo | Antes del 23/07/2025 (desde 2023/24) | Después | 
|---|---|---|
| Pre-cierre | media 0,0060 · p90 0,0126 | media 0,0062 · p90 0,0129 |
| **Cierre** | media 0,0060 · p90 0,0126 | **media 0,0127 · p90 0,0304** |

Además, la cobertura de Pinnacle cae al 38-39% en 2025/26 y al 0% en 2026/27.
**Consecuencia:** el benchmark "Pinnacle de cierre" no sirve desde 2025/26, que es parte
del período propuesto como prueba final. Se usarán como referencia el promedio de cierre
y Bet365 de cierre.

### 2.8 Estadísticas descriptivas dependientes del resultado (solo temporadas NO selladas)
Calculadas solo con temporadas ≤ 2023/24 (salvaguarda de prueba final):
- Tasa de Over 2,5: 48,8% (2000/01-2023/24, 182.818 partidos); 50,0% en 2019/20-2023/24.
  Entre división-temporadas (n ≥ 200): p10 = 40,8%, p90 = 56,6%.
- Brier del mercado de cierre O/U sin margen (2019/20-2023/24, ~38.000 partidos):
  promedio 0,24058; Bet365 0,24052; Pinnacle 0,24055. Climatología del mismo período
  (dentro de muestra): ≈ 0,2500. **El mercado mejora a la climatología solo un ~3,8%
  (skill de Brier).** Hay poco margen absoluto de mejora y se necesitan muestras grandes
  para detectar diferencias.

## 3. The Odds API (complemento de pago)
Verificado en su sitio y documentación:
- Planes: Starter gratis (500 créditos/mes). 20K créditos por 30 USD/mes, 100K por
  59 USD/mes, 5M por 119 USD/mes, 15M por 249 USD/mes. Todos los planes de pago incluyen
  históricos.
- Históricos: mercados destacados (h2h, spreads, **totals**) desde el **6-jun-2020**, con
  snapshots cada 10 min (cada 5 min desde sep-2022). Mercados adicionales (props,
  córners `alternate_totals_corners`, tarjetas `alternate_totals_cards`) desde el
  **3-may-2023**, consultados evento por evento.
- Coste: 10 créditos × mercados × regiones por llamada histórica.
- **Coolbet aparece en la lista de casas (región `eu`).** Es la única vía encontrada para
  cuotas históricas de Coolbet.
- **No verificado (requiere clave):** si Coolbet publica O/U con línea 2,5 en las 22
  divisiones, desde qué fecha y con qué completitud. El mercado `totals` devuelve la línea
  principal de cada casa, que puede no ser 2,5.
- Estimación de orden de magnitud (supuesto: ~2 snapshots por jornada con todos los
  partidos de la liga, 1 mercado, 1 región): ~1.000 créditos por liga-temporada. El plan de
  59 USD (100K créditos) alcanzaría para ~100 liga-temporadas en un mes. **Estimación no
  verificada; requiere prueba con clave.**

## 4. Fuentes NBA
- **SportsbookReviewsOnline:** temporadas 2007-08 a 2022-23. El sitio dice "will not be
  updated". En 2022-23: 664 partidos, columnas `Open/Close` (spread o total según la fila),
  `ML` y `2H`. Margen mediano del moneyline: 3,5% (p5 2,8%, p95 4,6%). **No identifica la
  casa ni el momento de captura del ML. Los totales no tienen precio.** Hay valores
  malformados (p. ej. `.5+03`). Calcular el EV de totales exigiría suponer -110, una cuota
  ficticia (prohibido).
- **stats.nba.com:** timeout desde este entorno. La comunidad documenta bloqueo de IPs de
  proveedores cloud (fuentes en issues de GitHub de librerías cliente). No se eludió.
- **Basketball-Reference / Sports Reference:** accesible. Términos de uso (actualizados el
  19-may-2023) prohíben usar su contenido para entrenar modelos de IA o "supporting machine
  learning methods used to predict, classify, label, or score inputs". Límite de 20
  peticiones/min (10 en FBref/Stathead). **Inutilizable para este proyecto sin permiso.**
- Props individuales: solo The Odds API de pago, desde may-2023, casas mayoritariamente
  de EE. UU.

## 5. xG y estadísticas avanzadas de fútbol
- **FBref:** 403 con desafío anti-bot. Según fuentes secundarias (Awful Announcing, The IX),
  retiró sus estadísticas avanzadas (incluido xG) en enero de 2026 tras el fin del acuerdo
  con Opta. No se encontró declaración oficial en los resultados.
- **Understat:** respondió con una página de error/bloqueo. No se verificaron sus
  términos. No se intentó eludir.
- **StatsBomb Open Data:** 80 competición-temporadas de 24 competiciones (muchas de La Liga
  y Champions de la era Messi, Mundiales y ligas femeninas). Licencia propia
  (`LICENSE.pdf`). No permite construir series multi-temporada de una liga completa.
- **Conclusión:** **DATOS NO DISPONIBLES** de xG histórico gratuito, legal y accesible para
  las 22 divisiones. El xG queda fuera de la línea base (podría evaluarse
  prospectivamente desde 2026/27 con las columnas nuevas de Football-Data).

## 6. Coolbet (operador de referencia del usuario)
- El sitio web solo entrega la aplicación JavaScript (1 KB de HTML). No hay archivo
  histórico público de cuotas.
- **No hay cuotas históricas de Coolbet en Football-Data.** Toda evaluación económica
  histórica gratuita usará otros operadores (Bet365, promedio y máximo de mercado),
  rotulados explícitamente.
- Opciones: (a) comprar históricos de The Odds API (desde 2020); (b) registrar
  prospectivamente las cuotas de Coolbet a mano o con la API gratuita (500 créditos/mes)
  en el laboratorio de GATE 5.

## 7. Costes reales de implementación

| Concepto | Coste | Necesario para |
|---|---|---|
| Football-Data | 0 | GATE 1-4 (H1 completa y H2 con operadores de referencia) |
| Cómputo | 0 (equipo convencional; la auditoría completa tarda < 1 min) | Todo |
| Python y librerías | 0 | Todo |
| The Odds API histórico | 30-59 USD por mes de suscripción (pago único posible) | H2 específica de Coolbet desde 2020 |
| The Odds API gratis | 0 (500 créditos/mes) | Registro prospectivo limitado (GATE 5) |

## 8. Obstáculos técnicos principales
1. **Momento de captura aproximado:** la regla viernes/martes no viene por fila; habrá que
   reconstruirla con fecha, día de la semana y hora.
2. **Cambio de fuente de cuotas:** Betbrain (2005-2019) → Oddsportal (2019+). Los promedios
   y máximos no son comparables entre épocas: hay que analizar por régimen.
3. **Pinnacle inutilizable desde jul-2025.**
4. **Sin xG histórico:** los predictores se limitan a goles, tiros, tiros a puerta y córners.
5. **Ascensos y descensos:** hay que inicializar los equipos nuevos sin información futura.
6. **Formato heterogéneo** de los CSV antiguos (cabeceras, alias, columnas extra).
7. **Operador del usuario sin históricos gratuitos.**

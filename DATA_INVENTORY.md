# DATA_INVENTORY — Inventario de las 22 divisiones

Versión 1.0 · 2026-11-27 · GATE 1 · Generado con `python -m qsports reports` ·
Detalle completo por división-temporada (589 filas, 50+ columnas):
`reports/gate1/inventory_by_division_season.csv` · Resumen por división:
`reports/gate1/inventory_by_division.csv`

**Regla de acceso:** este inventario usa **solo metadatos de nivel 0** (presencia o validez
booleana de campos, conteos y nombres) para todas las particiones, incluidas las selladas.
Ninguna cifra de este documento depende de valores de cuotas ni de resultados de 2024/25
en adelante.

## 1. Fuente y restricciones de uso

| Aspecto | Estado |
|---|---|
| Fuente | Football-Data.co.uk (`mmz4281/<temporada>/data.zip`) |
| Licencia | Sin licencia formal. La página de descargas dice *"My data is free"*. Supuesto de trabajo: uso privado y de investigación con atribución; **no redistribuir los CSV** (no se incluyen en el repositorio ni en el archivo descargable) |
| Descarga | 2026-11-27 (fecha UTC por temporada en los manifiestos RAW) |
| Temporadas | 2000/01-2026/27 (27). EC solo desde 2005/06. La fuente tiene resultados desde 1993/94, pero sin cuotas O/U antes de 2002/03 |
| Términos de casas de apuestas | No aplican: las cuotas son históricas y publicadas por la fuente |

## 2. Cambios metodológicos de la fuente (afectan a todas las divisiones)

| Desde | Cambio | Impacto |
|---|---|---|
| 2002/03 | Primeras cuotas O/U 2,5 de casas individuales (Gamebookers 66-87%, Bet365 16-26%) | Pre-cierre parcial; fuera del período de comparación |
| 2005/06 | Promedio y máximo **Betbrain** (`BbAv`, `BbMx`) para 1X2, O/U y AH | Inicio del benchmark A |
| 2012/13 | Cierre 1X2 de Pinnacle | Solo 1X2 |
| 2012/13 | Árbitro casi ausente (4,9% frente a ~36% en temporadas vecinas) | Irrelevante para O/U |
| 2017/18 | Estadísticas (tiros, córners, tarjetas) en las 22 divisiones (antes, ~10) | Predictores de tiros disponibles en todas las ligas desde aquí |
| 2019/20 | Promedio y máximo pasan a **Oddsportal** (`Avg`, `Max`); se añaden cuotas de **cierre** (`C`); hora de inicio | Cambio de régimen del benchmark A; nace el benchmark B |
| 23/07/2025 | Pinnacle no fiable; excluido de promedios y máximos | Regla `PIN-2025-07-23` (período reservado) |
| 2026/27 | Columnas xG (`HxG`/`AxG`) | Solo prospectivo |

### Tabla A — Resumen por división

| Div | País | Competición | Temporadas | Partidos dev | Holdout | Prospectivo | O/U pre ≥05/06 (dev) | O/U cierre ≥19/20 (dev) | Elegible A ≥05/06 (dev) | Tiros (dev) | Córners (dev) | Árbitro (dev) | Tiros ≥90% desde | Filas anchas recuperadas | Codificación |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|
| B1 | Bélgica | Pro League (First Division A) | 2000/01–2026/27 (27) | 6552 | 623 | 108 | 100.0% | 100.0% | 100.0% | 29.6% | 29.6% | 0.0% | 2017/18 | 305 | utf-8-sig |
| D1 | Alemania | Bundesliga | 2000/01–2026/27 (27) | 7344 | 612 | 90 | 100.0% | 100.0% | 99.9% | 95.8% | 95.8% | 8.3% | 2000/01 | 272 | cp1252,utf-8-sig |
| D2 | Alemania | 2. Bundesliga | 2000/01–2026/27 (27) | 7344 | 612 | 108 | 99.9% | 100.0% | 99.9% | 39.4% | 39.4% | 8.3% | 2001/02 | 628 | cp1252,utf-8-sig |
| E0 | Inglaterra | Premier League | 2000/01–2026/27 (27) | 9120 | 760 | 110 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 2000/01 | 301 | cp1252,utf-8-sig |
| E1 | Inglaterra | Championship | 2000/01–2026/27 (27) | 13248 | 1104 | 204 | 100.0% | 100.0% | 99.6% | 100.0% | 100.0% | 95.8% | 2000/01 | 456 | cp1252,utf-8-sig |
| E2 | Inglaterra | League One | 2000/01–2026/27 (27) | 13096 | 1104 | 179 | 100.0% | 100.0% | 99.6% | 100.0% | 100.0% | 95.8% | 2000/01 | 714 | cp1252,utf-8-sig |
| E3 | Inglaterra | League Two | 2000/01–2026/27 (27) | 13136 | 1104 | 188 | 99.9% | 100.0% | 99.5% | 100.0% | 100.0% | 95.8% | 2000/01 | 698 | cp1252,utf-8-sig |
| EC | Inglaterra | National League (Conference) | 2005/06–2026/27 (22) | 10130 | 1104 | 224 | 99.5% | 100.0% | 99.0% | 58.6% | 58.6% | 94.3% | 2005/06 | 0 | cp1252,utf-8-sig |
| F1 | Francia | Ligue 1 | 2000/01–2026/27 (27) | 8797 | 612 | 99 | 100.0% | 100.0% | 100.0% | 80.1% | 75.8% | 0.0% | 2005/06 | 346 | utf-8-sig |
| F2 | Francia | Ligue 2 | 2000/01–2026/27 (27) | 9020 | 612 | 117 | 99.9% | 100.0% | 99.8% | 28.3% | 28.3% | 0.0% | 2017/18 | 647 | utf-8-sig |
| G1 | Grecia | Super League | 2000/01–2026/27 (27) | 5834 | 469 | 76 | 99.0% | 100.0% | 98.9% | 28.7% | 28.7% | 0.0% | 2017/18 | 96 | utf-8-sig |
| I1 | Italia | Serie A | 2000/01–2026/27 (27) | 8824 | 760 | 120 | 99.9% | 100.0% | 99.9% | 81.7% | 81.7% | 8.6% | 2005/06 | 192 | utf-8-sig |
| I2 | Italia | Serie B | 2000/01–2026/27 (27) | 10402 | 760 | 130 | 99.6% | 99.8% | 99.3% | 26.0% | 26.0% | 0.0% | 2017/18 | 861 | cp1252,utf-8-sig |
| N1 | Países Bajos | Eredivisie | 2000/01–2026/27 (27) | 7270 | 612 | 117 | 100.0% | 100.0% | 99.8% | 28.4% | 28.4% | 0.0% | 2017/18 | 288 | utf-8-sig |
| P1 | Portugal | Primeira Liga | 2000/01–2026/27 (27) | 6816 | 612 | 98 | 99.9% | 100.0% | 99.7% | 31.4% | 31.4% | 0.0% | 2017/18 | 256 | utf-8-sig |
| SC0 | Escocia | Premiership | 2000/01–2026/27 (27) | 5423 | 456 | 83 | 99.9% | 100.0% | 99.8% | 100.0% | 100.0% | 95.8% | 2000/01 | 386 | cp1252,utf-8-sig |
| SC1 | Escocia | Championship | 2000/01–2026/27 (27) | 4232 | 360 | 77 | 100.0% | 100.0% | 99.9% | 36.0% | 36.0% | 36.2% | 2000/01 | 202 | utf-8-sig |
| SC2 | Escocia | League One | 2000/01–2026/27 (27) | 4209 | 360 | 79 | 99.8% | 100.0% | 99.8% | 35.9% | 35.9% | 35.8% | 2000/01 | 196 | utf-8-sig |
| SC3 | Escocia | League Two | 2000/01–2026/27 (27) | 4207 | 360 | 74 | 99.8% | 100.0% | 99.8% | 35.8% | 35.8% | 35.8% | 2000/01 | 281 | utf-8-sig |
| SP1 | España | La Liga (Primera División) | 2000/01–2026/27 (27) | 9120 | 760 | 129 | 100.0% | 100.0% | 99.9% | 79.2% | 79.2% | 0.0% | 2005/06 | 112 | utf-8-sig |
| SP2 | España | Segunda División | 2000/01–2026/27 (27) | 11088 | 924 | 162 | 99.6% | 100.0% | 99.5% | 29.0% | 29.0% | 0.0% | 2017/18 | 601 | utf-8-sig |
| T1 | Turquía | Süper Lig | 2000/01–2026/27 (27) | 7609 | 648 | 108 | 99.4% | 98.4% | 99.0% | 31.7% | 31.7% | 0.0% | 2017/18 | 192 | utf-8-sig |
| **Total** | | | | **182821** | **15328** | **2680** | | | | | | | | | |

### Tabla B — Cobertura por temporada (todas las divisiones; % de partidos)

| Temp. | Partición | Partidos | Con resultado | O/U pre prom. | O/U pre B365 | O/U pre PIN | O/U pre GB | O/U cierre prom. | O/U cierre B365 | O/U cierre PIN | Elegible A | Tiros | Córners | Árbitro | Hora | xG | Fuente prom. |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2000/01 | dev | 7094 | 7094 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 45.8 | 45.8 | 48.1 | 0.0 | 0.0 |  |
| 2001/02 | dev | 7036 | 7036 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 48.4 | 48.4 | 48.5 | 0.0 | 0.0 |  |
| 2002/03 | dev | 7134 | 7134 | 0.0 | 15.7 | 0.0 | 66.4 | 0.0 | 0.0 | 0.0 | 0.0 | 31.6 | 31.7 | 31.7 | 0.0 | 0.0 |  |
| 2003/04 | dev | 7340 | 7340 | 0.0 | 24.4 | 0.0 | 81.4 | 0.0 | 0.0 | 0.0 | 0.0 | 35.0 | 35.0 | 30.8 | 0.0 | 0.0 |  |
| 2004/05 | dev | 7324 | 7324 | 0.0 | 25.8 | 0.0 | 86.6 | 0.0 | 0.0 | 0.0 | 0.0 | 35.1 | 35.1 | 30.9 | 0.0 | 0.0 |  |
| 2005/06 | dev | 7786 | 7786 | 99.9 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 99.9 | 53.4 | 48.6 | 39.8 | 0.0 | 0.0 | betbrain |
| 2006/07 | dev | 7810 | 7810 | 99.8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 99.8 | 58.5 | 58.5 | 40.9 | 0.0 | 0.0 | betbrain |
| 2007/08 | dev | 7810 | 7810 | 99.9 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 99.9 | 54.6 | 54.6 | 36.0 | 0.0 | 0.0 | betbrain |
| 2008/09 | dev | 7810 | 7810 | 99.5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 99.5 | 54.6 | 54.6 | 36.1 | 0.0 | 0.0 | betbrain |
| 2009/10 | dev | 7634 | 7634 | 99.7 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 99.7 | 55.2 | 55.2 | 36.3 | 0.0 | 0.0 | betbrain |
| 2010/11 | dev | 7744 | 7744 | 100.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 100.0 | 55.0 | 55.0 | 36.3 | 0.0 | 0.0 | betbrain |
| 2011/12 | dev | 7744 | 7744 | 99.6 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 99.6 | 55.0 | 55.0 | 36.3 | 0.0 | 0.0 | betbrain |
| 2012/13 | dev | 7744 | 7744 | 99.7 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 99.7 | 55.0 | 55.0 | 4.9 | 0.0 | 0.0 | betbrain |
| 2013/14 | dev | 7811 | 7810 | 99.9 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 99.9 | 54.6 | 54.6 | 36.1 | 0.0 | 0.0 | betbrain |
| 2014/15 | dev | 7876 | 7875 | 99.7 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 99.7 | 54.1 | 54.1 | 35.8 | 0.0 | 0.0 | betbrain |
| 2015/16 | dev | 7810 | 7810 | 100.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 99.9 | 54.6 | 54.6 | 36.1 | 0.0 | 0.0 | betbrain |
| 2016/17 | dev | 7810 | 7810 | 100.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 99.9 | 47.5 | 47.5 | 36.0 | 0.0 | 0.0 | betbrain |
| 2017/18 | dev | 7810 | 7810 | 100.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 99.8 | 92.9 | 92.9 | 43.0 | 0.0 | 0.0 | betbrain |
| 2018/19 | dev | 7690 | 7689 | 99.7 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 99.5 | 92.5 | 92.5 | 43.6 | 0.0 | 0.0 | betbrain |
| 2019/20 | dev | 6904 | 6904 | 99.8 | 99.7 | 98.9 | 0.0 | 100.0 | 99.9 | 99.8 | 99.8 | 93.5 | 93.5 | 40.8 | 100.0 | 0.0 | oddsportal |
| 2020/21 | dev | 7648 | 7648 | 99.9 | 99.4 | 99.2 | 0.0 | 100.0 | 99.6 | 99.7 | 99.0 | 93.7 | 93.7 | 40.5 | 100.0 | 0.0 | oddsportal |
| 2021/22 | dev | 7822 | 7822 | 100.0 | 99.7 | 99.8 | 0.0 | 100.0 | 100.0 | 99.9 | 99.4 | 93.5 | 93.5 | 42.3 | 100.0 | 0.0 | oddsportal |
| 2022/23 | dev | 7830 | 7830 | 99.6 | 99.5 | 99.2 | 0.0 | 99.6 | 99.6 | 99.4 | 98.9 | 92.5 | 92.5 | 42.9 | 100.0 | 0.0 | oddsportal |
| 2023/24 | dev | 7800 | 7800 | 100.0 | 99.9 | 99.3 | 0.0 | 100.0 | 100.0 | 99.6 | 99.2 | 92.9 | 92.9 | 43.0 | 100.0 | 0.0 | oddsportal |
| 2024/25 | holdout | 7681 | 7681 | 100.0 | 100.0 | 99.6 | 0.0 | 100.0 | 100.0 | 99.8 | 99.3 | 92.8 | 92.8 | 43.7 | 100.0 | 0.0 | oddsportal |
| 2025/26 | holdout | 7647 | 7646 | 99.8 | 99.7 | 38.2 | 0.0 | 100.0 | 100.0 | 38.7 | 98.4 | 92.8 | 92.8 | 43.9 | 100.0 | 0.0 | oddsportal |
| 2026/27 | prospective | 2680 | 2680 | 100.0 | 99.9 | 0.0 | 0.0 | 100.0 | 100.0 | 0.0 | 100.0 | 100.0 | 100.0 | 45.4 | 100.0 | 83.1 | oddsportal |

### Tabla C — Casas/agregados presentes en cabeceras (unión de divisiones)

| Temporadas | O/U pre | O/U cierre | 1X2 pre |
|---|---|---|---|
| 2000/01–2000/01 | — | — | GB,IW,LB,SB,WH |
| 2001/02–2001/02 | — | — | GB,IW,LB,SB,SY,WH |
| 2002/03–2003/04 | B365,GB | — | B365,GB,IW,LB,SB,SO,WH |
| 2004/05–2004/05 | B365,GB | — | B365,BW,GB,IW,LB,SB,WH |
| 2005/06–2006/07 | BbAv,BbMx | — | B365,BW,BbAv,BbMx,GB,IW,LB,SB,SJ,VC,WH |
| 2007/08–2011/12 | BbAv,BbMx | — | B365,BS,BW,BbAv,BbMx,GB,IW,LB,SB,SJ,VC,WH |
| 2012/13–2012/13 | BbAv,BbMx | — | B365,BS,BW,BbAv,BbMx,GB,IW,LB,PS,SJ,VC,WH |
| 2013/14–2014/15 | BbAv,BbMx | — | B365,BW,BbAv,BbMx,IW,LB,PS,SJ,VC,WH |
| 2015/16–2017/18 | BbAv,BbMx | — | B365,BW,BbAv,BbMx,IW,LB,PS,VC,WH |
| 2018/19–2018/19 | BbAv,BbMx | — | B365,BW,BbAv,BbMx,IW,PS,VC,WH |
| 2019/20–2023/24 | Avg,B365,Max,P | Avg,B365,Max,P | Avg,B365,BW,IW,Max,PS,VC,WH |
| 2024/25–2024/25 | Avg,B365,Max,P | Avg,B365,Max,P | 1XB,Avg,B365,BF,BFE,BW,Max,PS,WH |
| 2025/26–2025/26 | Avg,B365,Max,P | Avg,B365,Max,P | Avg,B365,BFD,BFE,BMGM,BV,BW,CL,LB,Max,PS |
| 2026/27–2026/27 | Avg,B365,Max | Avg,B365,Max | Avg,B365,BFD,BFE,BV,BW,Max,PP |

Notas de lectura:
- "O/U pre ≥05/06" = proporción de partidos con algún par pre-cierre válido (promedio o casa
  individual), desde 2005/06.
- "Elegible A" (nivel 0) = par promedio pre-cierre presente y con margen en rango, con
  resultado, sin ambigüedad de captura y sin duplicado.
- "Tiros ≥90% desde" = primera temporada con ≥90% de partidos con tiros. En la mayoría de
  las segundas divisiones y ligas pequeñas es **2017/18**.
- "Filas anchas" = filas con más campos que la cabecera, recuperadas sin pérdida
  (2001/02-2009/10).
- Las cifras de holdout y prospectivo son **conteos de filas** (nivel 0). 2025/26 incluye 1
  fila sin resultado (presencia).

## 3. Particularidades por división

| Div | Particularidad |
|---|---|
| B1 | Formato de liga con playoffs. Los archivos incluyen solo los partidos presentes en el CSV de liga |
| D1, D2 | Archivos cp1252 en 2000/01-2001/02 (detectado y decodificado). D2 2004/05 con cabecera repetida (`LB`) |
| E0-E3 | Árbitro disponible (≈96-100%). Estadísticas completas desde 2000/01 |
| EC | Desde 2005/06. Córners casi ausentes desde 2019/20 (5,8%). Alias "Boston" → "Boston Utd" |
| G1 | Archivos 2000/01-2004/05 con cabeceras `HT/AT` (alias normalizado). 2 partidos sin resultado (2014/15 Niki Volos-OFI; 2018/19 Panathinaikos-Olympiakos). Alias "OFI" → "OFI Crete" |
| N1 | Alias "Roda" → "Roda JC" y "Sparta" → "Sparta Rotterdam" |
| SC0-SC3 | Árbitro disponible. SC1 2004/05: alias "Raith" → "Raith Rvs" (variante en la misma temporada) |
| T1 | 2013/14: fila artefacto con `#REF!` (error de Excel en la fuente), excluida. Cobertura de cierre O/U algo menor (98,4%) |
| Todas | 2001/02-2009/10: filas con columnas extra recuperadas |

## 4. Universo de entrenamiento frente a subconjunto de comparación con el mercado

| Conjunto | Definición | Partidos (dev) |
|---|---|---:|
| Filas de desarrollo | Todas las filas parseadas 2000/01-2023/24 | 182.821 |
| **Universo de entrenamiento** | Fecha, equipos y resultado presentes, sin clave duplicada | **182.818** |
| **Subconjunto de comparación A** | Además: temporada ≥ 2005/06, par A válido, sin ambigüedad de captura | **146.350** |
| Subconjunto con cierre (B) | A + B válidos (2019/20-2023/24) | 37.953 |

**Exclusión de competiciones:** aplicando los criterios predefinidos
(`configs/exclusion_criteria.json`), **ninguna división ni división-temporada** queda por
debajo del 80% de elegibilidad. Se mantienen las 22.

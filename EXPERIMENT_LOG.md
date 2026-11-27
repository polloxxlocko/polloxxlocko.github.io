# EXPERIMENT_LOG — Registro de experimentos

Registro **append-only**. Cada entrada incluye fecha, objetivo, datos y versión, código,
resultado (incluidos los negativos) y qué conjuntos de datos se examinaron. Nunca se
borran entradas. Las correcciones se registran como entradas nuevas.

---

## E-000 · 2026-11-27 · Fase Cero: auditorías y selección de mercado

**Tipo:** auditoría descriptiva (sin modelos, sin backtests, sin estrategias).

**Código y salidas**
| Script | Salida |
|---|---|
| `phase0/download_football_data.py` | `data/raw/football_data/<temporada>/data.zip` + `manifest.jsonl` (SHA-256) |
| `phase0/audit_football_data.py` | `reports/phase0/football_data_*.csv`, `football_data_audit_summary.json`, `pinnacle_vs_b365_ou_fairprob_absdiff.csv` |
| `phase0/verify_references.py` | `research/references_verified.json` |
| `phase0/market_selection.py` (semilla 20261127) | `reports/phase0/market_selection_results.json`, `market_selection_tables.md` |

**Datos:** Football-Data.co.uk, temporadas 2000/01-2026/27, descargadas el 2026-11-27
(27 archivos, 17 MB). Versión identificada por los SHA-256 del manifiesto.

**Datos examinados (transparencia sobre el conjunto de prueba):**
- Cobertura, márgenes y comparación Pinnacle-Bet365: **todas** las temporadas. Solo usan
  cuotas y presencia de datos, no resultados.
- Estadísticas que dependen del resultado (tasa de Over 2,5, varianza/media de goles,
  Brier del mercado): **solo temporadas ≤ 2023/24**. Los resultados de 2024/25 en adelante
  **no se examinaron**.
- *Revelación:* el Brier del mercado de cierre se calculó para 2019/20-2023/24, que incluye
  el período de validación propuesto (2022/23-2023/24). Es una medida del benchmark, no de
  un modelo, y no ajusta ningún parámetro. Se registra por transparencia.

**Resultados principales**
1. 200.825 partidos; 0 duplicados reales; 0 incoherencias `FTR`; 10 cuotas < 1,01.
2. Cuotas O/U 2,5: pre-cierre desde 2005/06 (~100%); pre-cierre y cierre multi-casa desde
   2019/20 (~100%); Pinnacle cae al 38% (2025/26) y al 0% (2026/27).
3. Pinnacle de cierre post-23/07/2025: la discrepancia con Bet365 se duplica (media
   0,0060 → 0,0127; p90 0,0126 → 0,0304). Confirma empíricamente la advertencia de la fuente.
4. Sin cuotas de córners ni tarjetas. Árbitro solo en Inglaterra y Escocia. xG solo en 2026/27.
5. Brier de cierre O/U (2019/20-2023/24): 0,2406 frente a 0,25 de la climatología dentro de
   muestra.
6. Matriz de selección: empate exacto O/U 2,5 = 1X2 = 4,55. NBA ganador tercero (3,05).
   Córners y tarjetas no elegibles.
7. Criterios secundarios: O/U con 99,5% de precios ≤ 3,50 (1X2: 66,6%) y desviación del
   retorno 0,97 (1X2: 1,24).

**Problemas encontrados y correcciones (resultados negativos del proceso)**
- **5 de 56 DOIs escritos de memoria eran incorrectos:** hubacek2019, dixon_pope2004,
  gandar1998_nba, manner2016_nba, dawson2007. Resolvían a artículos de otros temas o daban
  404. Se corrigieron con búsqueda en Crossref y se re-verificaron. **Lección:** nunca
  citar sin verificar el DOI.
- En el primer análisis, el parser descartaba 6.302 filas con más campos que la cabecera
  y detectaba 755 "duplicados" falsos (alias `HT/AT`). Se corrigió el parser, que ahora
  recupera 8.038 filas y da 0 duplicados.
- Una afirmación preliminar (Paul y Weinbach 2002 como evidencia NBA) se corrigió tras
  leer el resumen: trata de totales **NFL**.
- El subagente que intentó leer Wheatcroft (2020) no pudo extraer el texto del PDF. Se
  extrajo localmente con `pdftotext` y se leyó.

**Decisiones abiertas:** ver `MARKET_SELECTION_REPORT.md` §9.

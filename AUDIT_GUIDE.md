# AUDIT_GUIDE — Guía para una auditoría independiente

Versión 1.0 · 2026-11-27 · Estado del proyecto: GATE 1 completado (pendiente de revisión);
GATE 2 no iniciado.

Este repositorio se publica para que un auditor independiente (humano o IA) evalúe la
calidad científica, estadística y técnica del proyecto. La guía explica qué contiene, qué
se excluyó y por qué, cómo reproducir cada fase y qué se verificó realmente.

## 1. Contenido publicado

| Categoría | Ubicación |
|---|---|
| Código fuente | `src/qsports/` (paquete), `phase0/` (scripts de la Fase Cero) |
| Pruebas automáticas | `tests/` (59 pruebas) |
| Dependencias | `pyproject.toml`, `requirements-lock.txt` (versiones exactas) |
| Configuración | `configs/` (particiones, confiabilidad por fuente, exclusiones, alias, matriz de selección) |
| Manifiestos de datos | `data/raw/football_data/manifest.jsonl`, `data/{holdout,reserve}/raw/football_data/manifest.jsonl`, `data/{holdout,reserve}/registry.json`, `data/processed/MANIFEST.json` |
| Registro de accesos al holdout | `data/{holdout,reserve}/ACCESS_LOG.jsonl` (vacíos: 0 accesos) |
| Informes de investigación | `RESEARCH_FOUNDATIONS.md`, `DATA_FEASIBILITY_REPORT.md`, `MARKET_SELECTION_REPORT.md` |
| Documentos de GATE 1 | `DATA_INVENTORY.md`, `DATA_QUALITY_REPORT.md`, `TEMPORAL_INTEGRITY_REPORT.md`, `HOLDOUT_PROTECTION_PROTOCOL.md`, `MARKET_BENCHMARK_SPECIFICATION.md`, `EXPERIMENTAL_PROTOCOL.md`, `MODEL_ROADMAP.md`, `GATE_1_REPORT.md` |
| Registro de experimentos y limitaciones | `EXPERIMENT_LOG.md`, `LIMITATIONS.md`, `ROADMAP.md`, `CLAUDE.md` |
| Salidas reproducibles | `reports/phase0/`, `reports/gate1/`, `research/references_verified.json` |

## 2. Exclusiones deliberadas

| Excluido | Motivo | Cómo lo obtiene el auditor |
|---|---|---|
| CSV/ZIP de Football-Data.co.uk | Sin licencia formal de redistribución ("My data is free") | `python -m qsports download`; integridad verificable con los SHA-256 de los manifiestos |
| **Conjunto de prueba final sellado** (2024/25-2025/26) y reserva histórica sellada (2026/27, partición `reserve`): RAW y procesados | Protección metodológica del holdout | Solo se publican el registro (ids hash, conteos, hashes; **sin cuotas ni resultados**) y el log de accesos |
| Resúmenes de artículos en texto plano | OpenAlex no los redistribuye por razones legales; derechos de las editoriales | `python phase0/verify_references.py` los regenera en `research/abstracts_local.json` (ignorado por git) |
| Credenciales, tokens, `.env` | No existen en el proyecto: el escaneo de todo el historial no encontró ninguno | — |
| Parquet procesados, entornos virtuales, cachés | Derivados regenerables | `python -m qsports build` |

**Nota sobre el holdout para el auditor.** Los datos de 2024/25+ son públicos en la fuente.
El sellado es un compromiso metodológico de *este* proyecto: no usarlos para ninguna
decisión hasta congelar el protocolo. Si el auditor analiza resultados de esas temporadas,
pedimos que lo declare y que sus recomendaciones no se basen en ellos. Si no, el conjunto
de prueba quedaría contaminado.

## 3. Historial de Git

- Los commits del proyecto conservan su orden, mensajes, autores y fechas.
- **Reescritura declarada (2026-11-27, antes de publicar):** se eliminaron de todos los
  commits los resúmenes en texto plano de `research/` (§2), sustituidos por banderas
  `abstract_available_*`. Ningún otro archivo cambió. Por eso los hashes de commit
  difieren de los del archivo `quantitative-sports-gate1.tar.gz` entregado antes (2fede67,
  a6c5b0d, db09639 → 5321d35, 2c96be6, 605808a).
- El contenido anterior de este repositorio (sitio "THE JOURNEY") se eliminó del árbol a
  petición del propietario, en un commit explícito. **Su historial se conserva** y puede
  recuperarse desde el commit `53a47ce`.

## 4. Reproducción

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-lock.txt && pip install -e .
python -m qsports download --first 0001 --last 2627   # enruta cada temporada a su partición

# Fase Cero (los scripts solo ven las temporadas de desarrollo)
python phase0/audit_football_data.py
python phase0/market_selection.py
python phase0/verify_references.py      # requiere red (Crossref, OpenAlex, Semantic Scholar)

# GATE 1
python -m qsports build
python -m qsports verify                # debe terminar con "ok": true
python -m qsports reports
python -m pytest
```

## 5. Reproducibilidad de la Fase Cero (verificada el 2026-11-27)

Se ejecutó todo lo anterior en un **clon limpio**, con entorno virtual nuevo creado desde
`requirements-lock.txt` y **descarga nueva** desde la fuente. Las 27 temporadas
descargadas tienen el mismo SHA-256 que la descarga original.

| Artefacto de la Fase Cero | Resultado de la reproducción |
|---|---|
| `reports/phase0/football_data_outcome_stats_unsealed.csv` | **Idéntico** byte a byte |
| Tasa de Over 2,5 (48,80%), razón varianza/media (1,011), Brier del mercado de cierre (0,24058 promedio; 0,24052 Bet365; 0,24055 Pinnacle), Brier Betbrain (0,24443) | **Idénticos** |
| `football_data_coverage_by_season(_div).csv`, filas de desarrollo (2000/01-2023/24) | **Idénticas** |
| `market_selection_tables.md` y todo el análisis de sensibilidad (Dirichlet, perturbaciones) | **Idénticos** |
| `research/references_verified.json` | **59/59 DOIs con metadatos bibliográficos idénticos**; búsquedas idénticas; banderas de Semantic Scholar 21/21 idénticas en los DOIs consultados entonces |
| Cifras que incluían temporadas hoy selladas (2024/25-2026/27) | **No reproducibles sin abrir el sello, por diseño.** Ver §5.1 |

### 5.1 Cifras de la Fase Cero que incluyeron temporadas hoy selladas

Se calcularon antes del sellado. Solo usaron cuotas y presencia de datos, sin resultados
(`HOLDOUT_PROTECTION_PROTOCOL.md` §5). Su reproducción actual, solo con desarrollo:

| Cifra original (Fase Cero) | Reproducción solo con desarrollo |
|---|---|
| 200.825 partidos (27 temporadas) | 182.818 (24 temporadas) |
| 55.943 partidos con cierre O/U (Bet365 + promedio) | 37.936 |
| ~169.428 con alguna cuota O/U pre-cierre | 151.433 |
| Medianas de margen "desde 2019/20" | Recalculadas con 2019/20-2023/24 |
| Diferencia Pinnacle-Bet365 antes/después del 23/07/2025 | Sin datos posteriores en desarrollo (la regla se basa en la declaración de la fuente) |
| Desempate O/U frente a 1X2: precios ≤ 3,50 = 99,45% / 66,64%; desviación del retorno 0,9744 / 1,2362 | 99,45% / 66,68%; 0,9744 / 1,2402. **Misma conclusión** |

## 6. Reproducibilidad de GATE 1 (verificada el 2026-11-27)

En el mismo clon limpio:
- **Hashes de contenido idénticos** al manifiesto versionado en los 7 artefactos:
  desarrollo, nivel 0, benchmarks, y holdout y reserva completos y de nivel 0. Los
  reservados se compararon por hash, sin abrirlos.
- Informes `reports/gate1/*` regenerados **idénticos**.
- `python -m qsports verify`: ok; `pytest`: **59/59**.

## 7. Defecto encontrado durante esta verificación (corregido)

`phase0/verify_references.py` no reintentaba ante HTTP 429 de Crossref o Semantic
Scholar, y **sobrescribía en silencio** el archivo verificado con 8 referencias vacías. Se
añadieron reintentos con espera exponencial (respetando `Retry-After`). Si alguna consulta
falla, el script ya no sobrescribe: guarda la salida parcial aparte y termina con error.
Tras la corrección, los 59 DOIs se verificaron idénticos. Registrado en
`EXPERIMENT_LOG.md` (E-002).

## 8. Puntos sugeridos para la auditoría

1. **Point-in-time:** regla de captura viernes/martes y corte estricto
   (`TEMPORAL_INTEGRITY_REPORT.md` §2-5, `src/qsports/temporal.py`). ¿Es suficientemente
   conservador? ¿La evidencia del gradiente de movimiento basta?
2. **Benchmark principal A** (promedio pre-cierre de la fuente) y cambio de régimen
   Betbrain → Oddsportal (`MARKET_BENCHMARK_SPECIFICATION.md`).
3. **Protección del holdout:** mecanismos, alcance real (solo uso accidental) y
   evaluación de la exposición previa (`HOLDOUT_PROTECTION_PROTOCOL.md` §3-5).
4. **Criterios de decisión preregistrados**, SESOI provisional (0,001 nats), supuestos de
   potencia (σ_Δ sustituto = 0,114; deff = 1,23) y bootstrap por bloques de semanas
   (`EXPERIMENTAL_PROTOCOL.md` §4-6).
5. **Selección del mercado:** empate en la matriz y desempate por criterios secundarios
   declarados (`MARKET_SELECTION_REPORT.md` §4-5).
6. **Decisiones por juicio:** 4 alias de equipos (`configs/team_aliases.json`); sellado
   conservador de 2026/27.
7. **Literatura:** niveles de verificación T/R/M (`RESEARCH_FOUNDATIONS.md` §0). Solo un
   estudio se leyó en texto completo.
8. **Limitación fundamental:** no hay cuotas históricas de Coolbet (`LIMITATIONS.md` F1).

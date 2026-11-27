# Quantitative Sports Intelligence

Investigación cuantitativa sobre si un modelo especializado puede mejorar, fuera de
muestra, las probabilidades del mercado **Over/Under 2,5 goles** en fútbol (22 divisiones
de Football-Data.co.uk), y si esa mejora generaría rentabilidad **simulada** con cuotas
reales. **No es un sistema de pronósticos ni de recomendaciones, y no automatiza
apuestas.**

**Estado:** GATE 0 aprobado · GATE 1 (infraestructura de datos) completado y pendiente de
revisión · GATE 2 no autorizado.

> **¿Auditas este proyecto?** Empieza por [`AUDIT_GUIDE.md`](AUDIT_GUIDE.md): contenido,
> exclusiones (datos de la fuente, holdout sellado, resúmenes de artículos), reproducción y
> resultados de la verificación de reproducibilidad.

## Requisitos
- Python ≥ 3.11 (probado con 3.13.18)
- Conexión a internet para descargar los datos (~17 MB)
- ~200 MB de disco

## Reconstrucción desde cero (otro ordenador)
```bash
# 1. Obtener el código
git clone https://github.com/polloxxlocko/polloxxlocko.github.io quantitative-sports && cd quantitative-sports

# 2. Entorno reproducible
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-lock.txt
pip install -e .

# 3. Descargar los datos (cada temporada va a su partición; dev / holdout / prospectivo)
python -m qsports download --first 0001 --last 2627

# 4. Construir: sella holdout y prospectivo, construye dev, benchmarks y manifiesto
python -m qsports build

# 5. Verificar integridad y protección (debe terminar con "ok": true)
python -m qsports verify

# 6. Informes de GATE 1 (inventario, calidad, diagnósticos temporales, Pinnacle)
python -m qsports reports

# 7. Pruebas automatizadas
python -m pytest
```

**Sobre los hashes:** los SHA-256 esperados de cada `data.zip` están en
`data/raw/football_data/manifest.jsonl` y en los `registry.json` de las particiones
selladas. Si Football-Data corrigiera un archivo histórico, `verify` lo detectará como
cambio de versión de datos. Hay que registrarlo antes de continuar.

## Estructura
| Ruta | Contenido |
|---|---|
| `src/qsports/` | Paquete: ingesta, temporalidad, protección del holdout, benchmarks, calidad, CLI |
| `configs/` | Particiones, confiabilidad por fuente, criterios de exclusión, alias de equipos |
| `data/raw/` | RAW de desarrollo (no versionado; manifiesto sí) |
| `data/holdout/`, `data/prospective/` | **Sellados.** Solo se versionan el registro y el log de accesos |
| `reports/gate1/` | Salidas reproducibles de GATE 1 |
| `tests/` | 59 pruebas (unitarias, protección del holdout, integración) |
| `phase0/` | Scripts históricos de la Fase Cero |

## Documentos (orden de lectura sugerido)
0. `AUDIT_GUIDE.md`: guía para auditores
1. `GATE_1_REPORT.md`: informe ejecutivo de GATE 1
2. `HOLDOUT_PROTECTION_PROTOCOL.md`, `MARKET_BENCHMARK_SPECIFICATION.md`,
   `EXPERIMENTAL_PROTOCOL.md`, `MODEL_ROADMAP.md`
3. `DATA_INVENTORY.md`, `DATA_QUALITY_REPORT.md`, `TEMPORAL_INTEGRITY_REPORT.md`
4. `LIMITATIONS.md`, `EXPERIMENT_LOG.md`, `CLAUDE.md`
5. Fase Cero: `MARKET_SELECTION_REPORT.md`, `DATA_FEASIBILITY_REPORT.md`, `RESEARCH_FOUNDATIONS.md`

## Licencia de datos
Football-Data.co.uk no publica una licencia formal ("My data is free"). Este repositorio
**no redistribuye** sus CSV: se descargan de la fuente y se verifican por hash.

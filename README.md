# Quantitative Sports Intelligence

Investigación cuantitativa sobre si un modelo especializado puede mejorar, fuera de
muestra, las probabilidades implícitas de un mercado deportivo (H1) y si esa mejora
genera valor esperado con precios reales (H2). **No es un sistema de pronósticos ni de
recomendaciones de apuestas, y no automatiza apuestas.**

**Estado:** Fase Cero completada. GATE 0 (selección de mercado) pendiente de aprobación.

## Empezar a leer
1. `MARKET_SELECTION_REPORT.md`: recomendación y decisiones pendientes.
2. `DATA_FEASIBILITY_REPORT.md`: qué datos existen de verdad.
3. `RESEARCH_FOUNDATIONS.md`: literatura verificada.
4. `CLAUDE.md`: reglas permanentes del proyecto.
5. `LIMITATIONS.md`, `ROADMAP.md` y `EXPERIMENT_LOG.md`.

## Reproducir la Fase Cero
Requiere Python ≥ 3.11 con `numpy`, `pandas` y `requests`.
```bash
python phase0/download_football_data.py --first 0001 --last 2627   # ~1 min, 17 MB
python phase0/audit_football_data.py
python phase0/verify_references.py      # requiere acceso a Crossref/OpenAlex
python phase0/market_selection.py
```
Los archivos RAW no se versionan. Su integridad se verifica con los SHA-256 de
`data/raw/football_data/manifest.jsonl`. Football-Data puede actualizar las temporadas en
curso, así que los hashes de 2026/27 cambiarán.

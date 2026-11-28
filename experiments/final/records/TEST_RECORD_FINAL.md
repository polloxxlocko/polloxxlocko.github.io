# TEST_RECORD_FINAL — Ejecuciones de Claude en la prueba final

Todas son de Claude, en el contenedor del proyecto. **No se atribuyen al auditor independiente**, que no ha
revisado aún la prueba final.

| # | Qué | Commit | Resultado |
|---|---|---|---|
| T1 | Comprobaciones previas: hash del protocolo, integridad RAW y nivel 0 del holdout, 0 accesos, `run_final.py verify`, `qsports verify` | `bb2f3d6^` (gate4.1, árbol limpio) | Todo correcto |
| T2 | **Evaluación única** `run_final.py run --out experiments/final/holdout_run` | `bb2f3d6` (árbol limpio) | Estados `started`, `opened` y `finished`; resultados en `experiments/final/holdout_run/results.json` |
| T3 | `python -m qsports verify` tras la apertura | `49971c7` | 13 de 13 controles verdaderos; `ok = false` solo porque el holdout ya no está sellado |
| T4 | `pytest` tras la apertura (sin guarda) | árbol de `49971c7` | 212 superadas, 4 fallos de pruebas dependientes del estado. **Incidente I-1:** una de ellas abrió el holdout real (2.ª entrada del registro de accesos) |
| T5 | Pruebas de la guarda y de las pruebas herméticas | árbol de trabajo | Superadas; registros sin cambios |
| T6 | `pytest` completo con la guarda | árbol de trabajo y `2e4078d` | 218 superadas; registros de accesos sin cambios |
| T7 | `pytest` formal | `2e4078d` | **218 superadas, 0 fallos** (`pytest_2e4078d.*`) |
| T8 | ZIP ligero final en entorno virtual limpio | ver más abajo | — |

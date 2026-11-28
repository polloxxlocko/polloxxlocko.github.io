# TEST_RECORD_GATE4 — Ejecuciones de Claude en GATE 4

Todas son de Claude, en el contenedor del proyecto (Python 3.13, Linux). **No se atribuyen al auditor
independiente.** Las comprobaciones del auditor están en `INDEPENDENT_AUDIT_RECORD.md`.

| # | Qué | Commit | Resultado |
|---|---|---|---|
| T1 | `tests/test_gate4_holdout_mode.py` (proyecto temporal, autorización ficticia, datos sintéticos) | `ec8b501` | 6 superadas |
| T2 | `tests/test_final_test.py` (ejecutor final, solo datos sintéticos, más la negativa en modo real) | `ec8b501` | 13 superadas, 1 omitida (sin especificación congelada todavía) |
| T3 | `tests/test_m4cal_audit.py` | `ec8b501` | 8 superadas |
| T4 | Ensayo del ejecutor final con datos reales **de desarrollo** (sin el holdout) | árbol de `ec8b501` | Archivos de modelo = GATE 3; hashes del dataset = autorizados; réplica de identidad bit a bit (M2 y M4-cal, 61.370 filas cada uno); 0 accesos |
| T5 | `python experiments/gate4/m4cal_audit.py` | árbol de `ec8b501` | `experiments/gate4/*.json` |
| T6 | `pytest` completo antes del commit de código | `ec8b501` | 205 superadas, 1 omitida |
| T7 | `run_final.py verify` tras congelar | `20af512` | Identidad e inputs correctos; dataset de desarrollo = autorizado |
| T8 | `pytest` formal | ver `pytest_<commit>.*` en esta carpeta | — |
| T9 | ZIP ligero de GATE 4 en entorno virtual limpio | ver más abajo | — |

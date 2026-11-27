# TEST_RECORD_GATE3 — Ejecuciones de Claude en GATE 3

Todas las ejecuciones son de Claude, en el contenedor del proyecto (Python 3.13, Linux). **Ninguna debe
atribuirse al auditor independiente.** Su ejecución de `pytest` y `audit-synthetic` sigue pendiente, a
la espera de que el usuario le adjunte el ZIP ligero.

| # | Qué | Commit | Resultado |
|---|---|---|---|
| T1 | Prueba de mutación de `tests/test_determinism.py` con el código anterior a la corrección | árbol de `ea5598d` sin la corrección | 2 fallos, como se esperaba (diferencias entre semillas) |
| T2 | `pytest` previo al commit de las correcciones | `ea5598d` | 178 superadas |
| T3 | Reproducción limpia completa + sensibilidad D-3 | `ea5598d` (árbol limpio) | 2.362 s + D-3; candidatos idénticos bit a bit a `a724e84` |
| T4 | Ensayo en seco del ejecutor contra la reproducción `a724e84`, sin cruzar la valla | código de `ea5598d` | Réplica de identidad bit a bit (3 × 61.370 filas); evaluación sobre temporadas de desarrollo; 0 entradas en el registro de la valla |
| T5 | Verificación de identidad sin autorización | `e339fc6` | Identidad correcta; sin autorización, rechazo (`FenceError`) |
| T6 | Evaluación única de GATE 3 | `3bf3750` (árbol limpio) | Ver `GATE_3_REPORT.md` |
| T7 | `pytest` formal | `2e04fca` | **175 superadas, 3 fallos**: pruebas dependientes del estado, ya con autorización real (ver `README.md`) |
| T8 | `pytest` formal | `a27897a` | **178 superadas, 0 fallos** (`pytest_a27897a.*`) |
| T9 | `python -m qsports verify` | `a27897a` | `ok`; 0/0 accesos registrados; valla con 4 cruces autorizados y 0 no autorizados |

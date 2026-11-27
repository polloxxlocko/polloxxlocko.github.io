# AUDIT_RUN — Ejecutar la auditoría de GATE 2

Todo lo de este documento funciona **sin abrir los conjuntos sellados**. Los niveles 1 y 2
del holdout y de la reserva no están en el paquete ni en el repositorio.

## 0. Entorno
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-lock.txt
pip install -e .
```

## 1. Sin datos de la fuente (solo código + datos sintéticos)
```bash
python -m pytest                   # unitarias, anti-filtración, metodología; las de integración se omiten sin datos
python -m qsports audit-synthetic  # pipeline completo M0-M4 en dos mundos sintéticos con verdad conocida
```
`audit-synthetic` termina con `"ok": true` si:
- con un mercado que ya incorpora la información deportiva, M4-sport **no** supera a M4-cal;
- con un mercado que la ignora, M4-sport **sí** la detecta;
- las predicciones no cambian al alterar el futuro.

## 2. Reanálisis de las predicciones guardadas (sin datos de la fuente)
- `experiments/gate2/predictions/*.parquet`: **todas** las predicciones fuera de muestra de
  todas las configuraciones (también las descartadas), con `match_id`, `config_id`,
  `block`, `p_over`, `fit_tau` y `train_max_date`. Los Poisson incluyen además `lam_h` y
  `lam_a`.
- `experiments/gate2/fitlogs/*.parquet`: un registro por ajuste (tiempo, iteraciones,
  convergencia, gradiente máximo, parámetros).
- `experiments/gate2/configs.json`, `runlog.json` (tiempos, CPU, memoria) y
  `results.json` (selecciones, decisiones de la escalera, comparaciones, diagnósticos,
  potencia).

Para recalcular métricas hacen falta los resultados (`over25`) de desarrollo. Se obtienen
con el paso 3 hasta `build`.

## 3. Reproducción completa con datos reales de desarrollo
```bash
python -m qsports download --first 0001 --last 2324   # solo desarrollo; no descarga temporadas reservadas
python -m qsports build                               # sin RAW reservado conserva el registro versionado
python -m pytest
python experiments/gate2/run.py poisson_tuning
python experiments/gate2/run.py m3_tuning
python experiments/gate2/run.py inner_base
python experiments/gate2/run.py m4
python experiments/gate2/run.py evaluate
```
Sin las temporadas reservadas, `python -m qsports verify` marcará como no verificable la
integridad de los RAW sellados. Es lo esperado: esa comprobación pertenece al custodio.
La etapa `evaluate` usa, para la potencia, el conteo de nivel 0 de filas elegibles del
holdout. Si no existe, lo indica.

## 4. Valla de GATE 3
`qsports.walkforward.run` se niega a evaluar temporadas posteriores a 2021/22
(`FenceError`). El bloque 2022/23-2023/24 no se usó en GATE 2.

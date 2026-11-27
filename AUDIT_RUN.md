# AUDIT_RUN — Ejecutar la auditoría de GATE 2 / GATE 2.1

Todo lo de este documento funciona **sin abrir los conjuntos sellados**. Los niveles 1 y 2
del holdout y de la reserva no están en el paquete ni en el repositorio. Solo se versionan
sus metadatos de nivel 0 necesarios para fallar cerrado: registros de identificadores
(`registry.json`), registros de accesos (vacíos) y manifiestos de hashes.

## 0. Entorno
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-lock.txt
pip install -e .
```

## 1. Sin datos de la fuente (solo código + datos sintéticos)
```bash
python -m pytest                   # unitarias, anti-filtración, metodología, caché, protección; las de integración se omiten sin datos
python -m qsports audit-synthetic  # pipeline completo M0-M4 en dos mundos sintéticos con verdad conocida
```
`audit-synthetic` termina con `"ok": true` si:
- con un mercado que ya incorpora la información deportiva, M4-sport **no** supera a M4-cal;
- con un mercado que la ignora, M4-sport **sí** la detecta;
- las predicciones no cambian al alterar el futuro.

Muestra de datos sintéticos versionada: `data/synthetic/synthetic_sample_seed11.csv`
(generador, argumentos y SHA-256 en `data/synthetic/README.json`).

ZIP ligero (código, pruebas, configuración, documentación, dependencias, datos sintéticos;
**sin** Parquet de predicciones): `python -m qsports audit-package --light`.

## 2. Reanálisis de las predicciones guardadas (sin datos de la fuente)
- `experiments/gate2/predictions/<familia>/<config_id>.parquet`: **todas** las predicciones
  fuera de muestra publicadas en GATE 2 (también las descartadas), con `match_id`,
  `config_id`, `block`, `p_over` y `fit_tau`. Los Poisson incluyen además `lam_h` y `lam_a`
  (float32).
- **Dónde está `train_max_date`** (corregido en GATE 2.1): no en las predicciones, sino en
  `experiments/gate2/fitlogs/<familia>.parquet`, un registro por ajuste con `scope`,
  `fit_tau`, `n_train`, `train_max_date`, tiempo, iteraciones, convergencia y parámetros. Una
  predicción se enlaza con su ajuste por (`config_id`, `block`, `scope`, `fit_tau`), donde
  `scope` es la división del partido (Poisson, M0a) o `pooled` (M3, M4). Prueba:
  `tests/test_gate2_cache.py::test_train_max_date_stored_per_fit_and_joinable`.
- `experiments/gate2/configs.json`, `runlog.json` y `results.json`.

Para recalcular métricas hacen falta los resultados (`over25`) de desarrollo (paso 3 hasta `build`).

## 3. Reproducción completa con datos reales de desarrollo
```bash
python -m qsports download --first 0001 --last 2324   # solo desarrollo; no descarga temporadas reservadas
python -m qsports build                               # sin RAW reservado conserva el registro versionado
python -m pytest
python experiments/gate2/run.py all --out experiments/gate2_1/mi_repro --clean
python experiments/gate2/run.py m3_spec_sensitivity --out experiments/gate2_1/mi_repro
python experiments/gate2_1/compare_repro.py --repro experiments/gate2_1/mi_repro --out /tmp/mi_comparacion.json
python experiments/gate2_1/convergence_check.py
```
- `--clean` exige un directorio nuevo o vacío y un árbol de git sin cambios. No lee ninguna
  predicción, variable ni resultado previo, tampoco la caché `data/features/dev/`.
- `experiments/gate2/` (lo publicado en GATE 2) es de **solo lectura** para el pipeline.
- Cada ejecución escribe `RUN_MANIFEST.json`: commit, hashes de cada archivo de código y de
  configuración, hash de contenido del dataset de desarrollo, versiones, estado del sello y
  de la valla antes y después, y el SHA-256 de cada artefacto producido.
- Una salida solo se reutiliza (sin `--clean`) si tiene manifiesto de completitud con la
  misma clave de caché y el mismo SHA-256.

Sin las temporadas reservadas, `python -m qsports verify` marcará como no verificable la
integridad de los RAW sellados. Es lo esperado: esa comprobación pertenece al custodio. La
etapa `evaluate` usa, para la potencia, el conteo de nivel 0 de filas elegibles del holdout;
si no existe, lo indica.

## 4. Valla de GATE 3
`qsports.walkforward.run` se niega a evaluar temporadas posteriores a 2021/22 (`FenceError`)
salvo con `GATE3_AUTHORIZATION.json` ligado al hash de `configs/gate3_frozen_candidates.json`
(ninguno de los dos existe: GATE 3 no está autorizado). Todo intento queda en
`logs/GATE3_FENCE_LOG.jsonl` (vacío). El bloque 2022/23-2023/24 no se usó en GATE 2 ni en GATE 2.1.

## 5. Quién ejecutó qué
Los registros en `reports/gate2_1/` documentan **solo** las ejecuciones hechas por Claude
(commit exacto, entorno, comando y salida). Las comprobaciones del auditor independiente no
se reproducen aquí; el informe de auditoría recibido no detalla qué ejecutó. Ver
`reports/gate2_1/TEST_RECORD.md`.

# REPRODUCIBILITY_REPORT — Reproducción limpia de GATE 2 (GATE 2.1, exigencia 1)

Fecha: 2026-11-27 · Ejecutado por Claude en el contenedor del proyecto · Rama `gate2.1`

## 1. Qué se ejecutó

```bash
python experiments/gate2/run.py all --out experiments/gate2_1/repro_run --clean
python experiments/gate2/run.py m3_spec_sensitivity --out experiments/gate2_1/repro_run
python experiments/gate2/stability.py --out experiments/gate2_1/repro_run
python experiments/gate2_1/compare_repro.py --repro experiments/gate2_1/repro_run
```

| Propiedad | Valor (`experiments/gate2_1/repro_run/RUN_MANIFEST.json`) |
|---|---|
| Commit del código | `a724e84c29f05332c0a40903b8b9f4c9624029a6`, árbol limpio (`git_dirty: false`) |
| Modo | `--clean`: directorio nuevo y vacío; no se leyó ninguna predicción, variable ni resultado previo, incluida la caché `data/features/dev/` (`reads_published_outputs: false`) |
| Hash del código (archivos de `src/qsports`, `run.py`, `configs`, lockfile, `pyproject`) | `6878ed920bd6e90e83ab49cacc4e8fd8517d67721dc28e8b69b94a1b38e2d01b` (hash de cada archivo en el manifiesto) |
| Dataset de desarrollo (hash de contenido) | `41d9503c…f5b9`, igual al de `data/processed/MANIFEST.json`; benchmarks `c2b1dd65…42e5`; 182.821 filas |
| Hilos BLAS | 1 por proceso (`OPENBLAS/OMP/MKL_NUM_THREADS = 1`) |
| Duración | `all`: 2.400 s (inicio 11:08:32 UTC); `m3_spec_sensitivity`: 208 s (fin 11:52:12 UTC) |
| Artefactos | 397 archivos con SHA-256 en el manifiesto; conjunto: `artifacts_set_sha256`. Los Parquet no se versionan (`.gitignore`), pero sus hashes sí |
| Holdout y reserva | No se descargaron ni se abrieron. Accesos registrados antes y después: 0/0 (`sealed_unchanged: true`). Para la potencia se leyó el conteo de **nivel 0** del holdout (metadatos permitidos), como en GATE 2 |
| Bloque de validación 2022/23-2023/24 | No evaluado. Registro de la valla: 0 intentos permitidos y 0 rechazados |

Registros de consola: `experiments/gate2_1/logs/`.

## 2. Comparación con lo publicado en GATE 2 (`experiments/gate2_1/repro_comparison.json`)

| Aspecto | Resultado |
|---|---|
| Configuraciones | Publicadas 99, reproducidas 98. Solo en lo publicado: `M2__h240_r16_pp` (ver §3.1) |
| Filas de predicción comparadas (unión 1:1 por `match_id`) | 6.485.374 en 98 configuraciones; 0 filas presentes solo en un lado |
| Predicciones idénticas bit a bit | **6.474.400 (99,83%)**. Las 10.974 restantes son todas de una sola configuración, `M2__h480_r64_pp` (máx. \|Δp\| = 8,5·10⁻⁹; ver §3.2) |
| `fit_tau`, `n_train`, `train_max_date` por ajuste | Iguales en todas las configuraciones comparables |
| Ajustes marcados no convergentes | Publicados 226, reproducidos 224. La diferencia: 1 de `M2__h240_r16_pp` (no reproducida) y 8 frente a 7 en `M2__h480_r64_pp` (§3.2) |
| Selecciones y decisiones de la escalera | Todas iguales: M1* `w1095_r128`, M2* `h480_r64`, prior de ascendidos no adoptado, M3* `GSTC_h15_r100`, tiros fuera de M4-sport, M4-cal* `h730`, M4-sport* `h730_r1000` |
| Ruta de extensión de grilla D-1 | Idéntica en las 5 familias (mismas grillas y mismo óptimo en cada paso) |
| Tablas de selección (log loss) | Máx. \|diferencia\| = 2,2·10⁻¹⁶ (la log loss exacta usa `log1p(−p)` en lugar de `log(1−p)`) |
| Prueba interna con el método publicado (semanas activas) | Δ̄ e IC con máx. \|diferencia\| = 6,9·10⁻¹⁸; las 13 categorías, iguales |
| Prueba interna con el método corregido (semanas calendario) | Ninguna de las 13 categorías cambia respecto de lo publicado (`reports/gate2_1/TABLES.md`, T1) |
| Diagnósticos M5 y N de potencia | Iguales (dispersión 1,017; r = 0,0135; N = 15.154) |

## 3. Diferencias y su explicación

### 3.1 `M2__h240_r16_pp` (solo en lo publicado)
La primera ejecución `all` de GATE 2 se detuvo para aplicar D-1 (`EXPERIMENT_LOG.md` E-004;
`experiments/gate2/log_all_run1_stopped_D1.txt`, único registro que la menciona). Antes de D-1, el
candidato de la etapa 1 de M2 era `h240_r16`, y se calculó su variante con prior de ascendidos. Tras
D-1, la etapa 1 eligió `h480_r64`, así que una ejecución limpia nunca calcula `h240_r16_pp`. Esa
configuración no entró en ninguna decisión publicada (`results.json → M2_promoted_candidate =
M2__h480_r64_pp`). Su presencia confirma lo que la auditoría señaló: lo publicado mezclaba salidas de
más de una ejecución.

### 3.2 No determinismo en el prior de ascendidos (hallazgo de GATE 2.1)
`PoissonModel` con `promoted_prior=True` promedia las fuerzas de los equipos descendidos recorriendo
un `set` de nombres. El orden de iteración de un `set` de cadenas depende de `PYTHONHASHSEED`
(aleatorio por proceso), y la suma en coma flotante depende del orden. Comprobación ejecutada por
Claude, en la división T1 con `M2__h480_r64_pp`:
- semillas 0, 1 y 2 → máx. \|Δp\| = 6,6·10⁻⁹ y 5,1·10⁻⁹, con 0, 1 y 0 ajustes marcados no
  convergentes;
- la misma semilla dos veces → resultados idénticos.

Alcance: solo las configuraciones `_pp`, que no fueron seleccionadas ni son candidatas. La
diferencia en log loss entre `h480_r64_pp` y `h480_r64` (1,8·10⁻⁵) es más de mil veces mayor que el
efecto de ese ruido, así que la decisión no cambia. **Corrección propuesta, no aplicada:** iterar `sorted(departed)`. No la
apliqué en GATE 2.1 porque modifica el código del modelo después de la reproducción oficial, y la
reproducción debe corresponder a un commit exacto. Queda como decisión pendiente (`GATE_2_1_REPORT.md` §8).

## 4. Qué demuestra y qué no

- Demuestra que, con los datos de desarrollo y el código de `a724e84`, una ejecución desde cero
  reproduce las selecciones, las decisiones y las categorías publicadas, y el 99,83% de las
  predicciones bit a bit. El resto difiere por debajo de 10⁻⁸ por una causa identificada.
- No demuestra que las cachés antiguas de GATE 2 fueran correctas en general: muestra que en esta
  ocasión no alteraron los resultados.
- No sustituye la verificación por un tercero en otra máquina. El ZIP ligero y `AUDIT_RUN.md`
  permiten repetir todo lo anterior sin datos sellados.

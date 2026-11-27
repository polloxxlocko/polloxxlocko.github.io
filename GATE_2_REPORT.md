# GATE_2_REPORT — Informe ejecutivo de GATE 2 (Modelos y validación interna)

Fecha: 2026-11-27 · Estado: **COMPLETADO; auditoría independiente: aprobación metodológica
condicionada** · GATE 3: **no iniciado ni autorizado** · Holdout y reserva: **sellados, 0 accesos
registrados** · Bloque de validación 2022/23-2023/24: **vallado, sin usar**

> **Nota de GATE 2.1 (2026-11-27).** Este informe se conserva como registro de GATE 2. La auditoría
> encontró problemas de reproducibilidad, evaluación, validación, protección, convergencia,
> documentación e interpretación. Las correcciones, la reproducción limpia y los resultados con el
> método corregido están en `GATE_2_1_REPORT.md`, `AUDIT_RESPONSE_GATE2.md` y
> `REPRODUCIBILITY_REPORT.md`. Las frases de interpretación marcadas *[corregido en GATE 2.1]* se
> reescribieron para limitarlas a lo evaluado. Los IC de esta página usan bloques de semanas
> **activas** (desviación D-4).

## 1. Resumen

La infraestructura de evaluación (evaluador estadístico + walk-forward con controles
anti-filtración) se construyó y probó primero. Después se ajustaron y evaluaron M0-M4
siguiendo un preregistro con dos desviaciones documentadas.

**Resultado central (desarrollo, prueba interna 2014/15-2021/22, n = 61.137):**
- Los modelos deportivos superan a la frecuencia histórica (S-R), pero son **claramente
  peores que el mercado** pre-cierre: M2 − A = +0,0048 nats, I-R, en todas las temporadas.
- Recalibrar el mercado (M4-cal) **no** lo mejora de forma distinguible: −0,00008, EQ.
- *[corregido en GATE 2.1]* **Con M4-sport definido por la desviación logit p_M2* − logit p_A,
  no se demostró aporte incremental sobre una recalibración del mercado en 2014/15-2021/22:**
  M4-sport − M4-cal = −0,00001 [−0,00006; +0,00004], **EQ**. El intervalo excluye una mejora
  del orden del mínimo efecto de interés (0,001) **para esa formulación y ese período**; no
  dice nada de otras variables, formulaciones o modelos.

Estos resultados **no son veredictos** de Q1-Q3 (eso exige GATE 3 y el holdout), pero
anticipan con fuerza un resultado **VENTAJA ESTADÍSTICA NO DEMOSTRADA** en Q2 para este
conjunto de información (goles, tiros, córners, cuotas pre-cierre de consenso).

## 2. Cumplimiento de las 10 exigencias

| # | Exigencia | Cómo se cumplió | Evidencia |
|---|---|---|---|
| 1 | Categorías de decisión excluyentes | Partición en 6 categorías (S-R, S-NR, EQ, INC, I-NR, I-R), verificada con predicados independientes sobre 20.000 pares y todos los bordes | `EXPERIMENTAL_PROTOCOL.md` §6; `test_decision_partition_is_exclusive_and_exhaustive` |
| 2 | Reserva 2026/27 frente a prospectiva genuina | Partición renombrada `prospective` → `reserve`; protocolo de validación prospectiva con predicciones publicadas antes de cada partido | `EXPERIMENTAL_PROTOCOL.md` §10; `HOLDOUT_PROTECTION_PROTOCOL.md` §7 |
| 3 | Evaluador y walk-forward antes que los modelos | Evaluador (23 pruebas) y motor (10 pruebas) construidos y probados antes del primer modelo | Orden de commits; `EXPERIMENT_LOG.md` E-003 |
| 4 | M4-cal separado de M4-sport | Mismo procedimiento, mismas filas, mismos pesos; solo difiere el término deportivo. Validado en mundos sintéticos: sin falso positivo cuando el mercado es completo y con detección cuando no lo es | `test_m4_sport_vs_cal_detects_incremental_information_only_when_present`; `qsports audit-synthetic` |
| 5 | Pruebas contra filtraciones en todo el pipeline | Entrenamiento < τ (aserción), lista blanca de columnas al predecir, invariancia al futuro (6 modelos), independencia de lote, features por fuerza bruta, selección limitada al ajuste, valla GATE 3 | `tests/test_walkforward.py`, `test_models.py`, `test_gate2_selection.py` |
| 6 | Conservar todas las predicciones fuera de muestra | 91 configuraciones (incluidas las descartadas; 3 de ellas benchmarks) y la ejecución abortada, ~6,6 M de filas | `experiments/gate2/predictions/<familia>/<config>.parquet` |
| 7 | Tiempos, convergencia, consumo y estabilidad | Registro por ajuste y por configuración; análisis de convergencia con impacto medido; estabilidad por temporada, régimen, vecinos y parámetros | `fitlogs/`, `runlog.json`, `stability.json` |
| 8 | Paquete de auditoría reproducible sin datos sellados | `python -m qsports audit-synthetic`, `python -m qsports audit-package`, `AUDIT_RUN.md` | §6 de este informe |
| 9 | Complejidad solo si está justificada | Escalera con reglas preregistradas: M2 sí (S-NR sobre M1); tiros en M4 no (H1b EQ); M5 no (diagnósticos bajo umbral) | `MODEL_SPECIFICATION.md` §B1 |
| 10 | No avanzar a GATE 3 | Valla activa; bloque de validación sin usar; holdout y reserva sin accesos | `FenceError`; `ACCESS_LOG` vacío |

## 3. Resultados principales

### 3.1 Escalera (bloque de ajuste 2005/06-2013/14)
| Decisión | Resultado | Acción |
|---|---|---|
| M2 sobre M1 | −0,00057 [−0,00080; −0,00035], S-NR | M2 adoptado |
| Prior de ascendidos en M2 | No mejora | No adoptado (se mantiene lo simple) |
| Tiros sobre goles (H1b, dentro de M3) | −0,00003 [−0,00024; +0,00018], EQ | Los tiros no entran en M4-sport |
| Binomial negativa | Dispersión 1,017 [1,005; 1,030] < 1,10 | No implementada |
| Poisson bivariado | r = 0,0135 [0,0055; 0,0216], \|r\| < 0,05 | No implementado |
| Gradient boosting | Sin no linealidad documentada | No implementado |

### 3.2 Prueba interna 2014/15-2021/22 (una evaluación por familia)
| Comparación | Δ log loss [IC95] | Categoría |
|---|---|:---:|
| M2 − C (deporte frente a frecuencia) | −0,00593 [−0,00677; −0,00510] | S-R |
| M2 − M1 | −0,00073 [−0,00098; −0,00047] | S-NR |
| M3 − M2 | +0,00075 [+0,00017; +0,00133] | I-NR |
| **M2 − A** (deporte frente a mercado) | **+0,00480 [+0,00398; +0,00562]** | **I-R** |
| M4-cal − A (recalibración) | −0,00008 [−0,00020; +0,00004] | EQ |
| **M4-sport − M4-cal** (aporte deportivo incremental) | **−0,00001 [−0,00006; +0,00004]** | **EQ** |

Calibración: el mercado A tiene pendiente 1,103, es decir, probabilidades algo
comprimidas. M4-cal la lleva a 1,003, sin ganancia distinguible de log loss. Los modelos
Poisson están bien calibrados (pendiente 1,00-1,01).

### 3.3 Potencia para el holdout
Con N = 15.154 filas elegibles (conteo de nivel 0), el MDE es 0,00014-0,00036 nats para
las comparaciones de M4, muy por debajo de δ = 0,001. Para M2 frente a A, el MDE (0,0022)
supera δ. *[corregido en GATE 2.1]* El MDE mide la potencia para detectar **superioridad**,
no para demostrar **equivalencia**; ambas se calculan por separado en `GATE_2_1_REPORT.md`.

## 4. Problemas encontrados (todos registrados en `EXPERIMENT_LOG.md`)

| Problema | Resolución |
|---|---|
| Grilla preregistrada sin acotar el óptimo (selección en el borde) | Desviación D-1: regla uniforme de extensión, decidida antes de ver M3, M4 y la prueba interna. M1 sigue en el borde tras 3 extensiones (limitación) |
| L-BFGS-B lento (59 ms/ajuste) | D-2: Newton-Raphson con Hessiana analítica (7,8 ms; óptimo igual o mejor) |
| Sobresuscripción de hilos BLAS (243 s frente a 22 s por configuración) | 1 hilo por proceso; ejecución abortada conservada; diferencia de p ≤ 6,7·10⁻⁹ |
| 226 ajustes Poisson "sin convergencia" | Precisión límite del criterio de Armijo (gradiente ≤ 2·10⁻⁵); reajuste de alta precisión: \|Δp\| ≤ 2,1·10⁻⁹ |
| La prueba de invariancia de M3 falló | Error de especificación de la **prueba** (reajuste cada 4 capturas), no del modelo; corregida |
| Error en la sintaxis de selección (`query`) | Corregido; las configuraciones ya calculadas se reutilizaron |
| Un commit con 1 prueba fallida (tripwire sobre `audit_package.py`) | La tripwire funcionó; marcas centralizadas en `holdout.py`; commits posteriores condicionados a pytest |
| Archivos de predicciones > 50 MB | Un archivo por configuración; `p_over` exacto bit a bit verificado |
| El verificador del paquete rechazaba los manifiestos de hashes versionados (falso positivo) | Revisa solo archivos con una función pura y probada (`is_forbidden`); los datos sellados siguen prohibidos |

## 5. Limitaciones relevantes para la interpretación
1. Espacio de información limitado: sin xG histórico, alineaciones, lesiones, clima ni
   motivación. El resultado negativo se refiere a **este** conjunto de información.
2. La prueba interna es de desarrollo. La confirmación formal requiere GATE 3
   (validación) y la apertura única del holdout.
3. M1 terminó en el borde de la grilla de ridge (no afecta a las conclusiones: M2 es
   mejor y es el que alimenta a M4).
4. El benchmark A es el consenso de cuotas pre-cierre. Batirlo no implicaría batir a cada
   casa individual ni el precio de cierre.
5. Q3 (rentabilidad) no se evaluó en GATE 2. *[corregido en GATE 2.1]* La equivalencia
   predictiva en desarrollo **no** demuestra una rentabilidad simulada negativa ni positiva:
   eso solo puede establecerlo Q3, con la regla de selección y los precios observados.

## 6. Paquete de auditoría
```bash
pip install -r requirements-lock.txt && pip install -e .
python -m pytest                  # 115 pruebas (las 15 de integración se omiten sin datos)
python -m qsports audit-synthetic # pipeline M0-M4 en mundos sintéticos; termina con "ok": true
python -m qsports audit-package   # dist/audit_package_gate2.tar.gz (git archive verificado)
```
Detalle en `AUDIT_RUN.md`. Ningún paso requiere abrir el holdout ni la reserva.

**Verificación del paquete (commit 5142044):** se extrajo en un directorio vacío y se instaló
en un entorno virtual limpio con `requirements-lock.txt`. Resultado: 100 pruebas superadas y
15 omitidas (integración, sin datos de la fuente). `audit-synthetic` terminó con `"ok": true`
en 43 s. El paquete pesa 186 MB, casi todo predicciones guardadas, y tiene 208 archivos.
Contiene los manifiestos de hashes de las particiones selladas (nivel 0), pero ningún ZIP,
CSV ni parquet sellado.

## 7. Recomendaciones para GATE 3 (requiere tu autorización)
1. **Candidatos congelados:** M4-sport (h730, r1000, X = desviación de M2*), M4-cal (h730)
   y M2* (modelo independiente). Una evaluación en 2022/23-2023/24 con la partición del §6.
2. **Mantener δ = 0,001.** La potencia del holdout es suficiente para las comparaciones de
   M4.
3. **Expectativa honesta:** *[corregido en GATE 2.1]* la evidencia de desarrollo hace
   probable que GATE 3 vuelva a dar EQ para M4-sport − M4-cal con esta formulación y que Q2
   termine en VENTAJA ESTADÍSTICA NO DEMOSTRADA para estos candidatos. Abrir el holdout seguiría teniendo valor: es el único veredicto formal y
   preregistrado.
4. **Alternativa legítima:** detener la línea aquí y documentar el resultado negativo, o
   ampliar el conjunto de información (p. ej. xG prospectivo desde 2026/27). Esto último
   requeriría una decisión explícita de alcance, porque cambia el universo de datos.

## 8. Decisiones que necesito de ti
1. ¿Apruebas GATE 2?
2. ¿Aceptas las desviaciones D-1 (extensión de grilla) y D-2 (optimizador Newton)?
3. ¿Autorizas GATE 3 con los candidatos del §7, o prefieres detener o replantear la línea?
4. La rama `gate2` está en GitHub como rama aparte (`main` y el sitio no cambian). ¿Quieres
   fusionarla con `main` después de revisarla?

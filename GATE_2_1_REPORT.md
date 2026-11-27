# GATE_2_1_REPORT — Fase correctiva tras la auditoría de GATE 2

Fecha: 2026-11-27 · Rama: `gate2.1` (no fusionada con `main`) · Estado: **completado, pendiente de
revisión** · GATE 3: **no autorizado, no iniciado** · Holdout y reserva: **sellados, 0 accesos
registrados** · Bloque de validación 2022/23-2023/24: **vallado, 0 intentos registrados**

Documentos hermanos: `AUDIT_RESPONSE_GATE2.md` (respuesta punto por punto),
`REPRODUCIBILITY_REPORT.md` (reproducción limpia y comparación), `reports/gate2_1/TABLES.md` (todas
las tablas, generadas desde los JSON), `reports/gate2_1/TEST_RECORD.md` (qué ejecutó Claude y qué no
consta del auditor) y `reports/gate2_1/HASH_MANIFEST.json`.

## 0. Resumen

- **Los nueve bloques de hallazgos se confirmaron** en el código o en los documentos y se corrigieron.
  No encontré ninguno incorrecto (matices en `AUDIT_RESPONSE_GATE2.md` §10).
- **Reproducción limpia** desde cero (commit `a724e84`, árbol limpio, sin leer nada previo):
  - mismas selecciones, misma ruta de grilla D-1 y mismas 13 categorías de la prueba interna;
  - 99,83% de las 6,49 M de predicciones idénticas bit a bit;
  - el resto (una configuración no seleccionada) difiere por debajo de 10⁻⁸ por un no determinismo
    que identifiqué y documento (§2).
- **Método corregido** (bootstrap por semanas calendario): ninguna categoría cambia. Tampoco cambia
  con bloques de 2, 4, 8 o 12 semanas ni con la definición de semana. La autocorrelación semanal
  real de Δ es baja (r₁ entre −0,05 y +0,14).
- **Los 226 ajustes no convergentes**, verificados uno a uno:
  - los 226 alcanzan un criterio 100 veces más estricto;
  - las soluciones publicadas ya eran óptimas a precisión de máquina (|Δf| ≤ 6,8·10⁻¹³);
  - |Δp| ≤ 2,7·10⁻⁸ e impacto en la log loss media ≤ 4,5·10⁻¹².
- **D-3:** con la forma preregistrada log(1 + partidos previos), M3 elige la misma configuración y
  la decisión H1b no cambia.
- **Conclusión de desarrollo, acotada:** en 2014/15-2021/22, M4-sport (desviación logit p_M2* −
  logit p_A) frente a M4-cal da Δ = −0,00001 [−0,00006; +0,00004], **EQ**: aporte incremental
  **no demostrado para esa formulación y ese período**. M2 frente al mercado A: +0,0048, **I-R**.
  Esto **no** es un veredicto de Q1-Q3 ni dice nada sobre la rentabilidad (Q3).

## 1. Qué se corrigió
| # | Exigencia | Corrección | Evidencia |
|---|---|---|---|
| 1 | Reproducibilidad real | Directorio por ejecución, `--clean`, cachés con manifiesto (clave + SHA-256), escrituras atómicas, `RUN_MANIFEST.json`, lo publicado en solo lectura, comparación fila a fila | `tests/test_gate2_cache.py` (8 pruebas); `REPRODUCIBILITY_REPORT.md` |
| 2 | Evaluador | Semanas calendario explícitas (D-4), sensibilidad 2/4/8/12, autocorrelación semanal, potencia de superioridad frente a equivalencia, pruebas bajo dependencia serial | `tests/test_evaluation_v21.py`; `experiments/gate2_1/evaluator_evidence.json`; §3 |
| 3 | Validación de entradas | `qsports.validation`; log loss exacta; universo explícito; cobertura del 100% en la prueba interna; uniones 1:1; sin `pivot_table` | `tests/test_evaluation_v21.py`; T5 |
| 4 | Protección del holdout | Fail-closed; `verify` exige 0 accesos en estado sellado; valla de GATE 3 con autorización ligada a candidatos congelados y registro de intentos (motor y universo de evaluación) | `tests/test_gate21_protection.py` (9 pruebas); `verify` |
| 5 | Convergencia | Verificación individual de los 226 ajustes | §4; `experiments/gate2_1/convergence_check.json` y `_fits.csv` |
| 6 | Documentación | D-3 con sensibilidad; ubicación de `train_max_date`; registros de pytest por commit; Claude frente al auditor | §5; `reports/gate2_1/` |
| 7 | Interpretación | Conclusiones limitadas a lo evaluado; sin inferencias de rentabilidad | §6 |

## 2. Reproducción limpia (detalle en `REPRODUCIBILITY_REPORT.md`)
| Aspecto | Resultado |
|---|---|
| Configuraciones | 98 reproducidas de 99 publicadas. `M2__h240_r16_pp` procede de la ejecución de GATE 2 detenida antes de D-1 y no intervino en ninguna decisión |
| Predicciones bit a bit | 6.474.400 de 6.485.374 (99,83%); 0 filas solo en un lado |
| Diferencias | Solo `M2__h480_r64_pp` (prior de ascendidos, no seleccionado): máx. \|Δp\| = 8,5·10⁻⁹. Causa: promedio sobre un `set` cuyo orden depende de `PYTHONHASHSEED`, confirmado con semillas 0, 1 y 2 |
| Selecciones, grillas D-1, decisiones | Idénticas |
| Prueba interna, mismo método | Máx. \|diferencia\| = 6,9·10⁻¹⁸; categorías idénticas |
| `train_max_date`, `n_train`, `fit_tau` | Idénticos |

## 3. Evaluador corregido: resultados (`reports/gate2_1/TABLES.md`, T1-T4)

**Prueba interna 2014/15-2021/22, n = 61.137, método principal (semanas calendario, bloque 4):**

| Comparación | Δ̄ log loss [IC 95%] | Categoría | ¿Igual que lo publicado? |
|---|---|:---:|:---:|
| M2 − C | −0,00593 [−0,00676; −0,00509] | S-R | sí |
| M2 − M1 | −0,00073 [−0,00099; −0,00048] | S-NR | sí |
| M3 − M2 | +0,00075 [+0,00016; +0,00131] | I-NR | sí |
| M2 − A | +0,00480 [+0,00394; +0,00562] | I-R | sí |
| M4-cal − A | −0,00008 [−0,00019; +0,00004] | EQ | sí |
| M4-sport − A | −0,00009 [−0,00021; +0,00004] | EQ | sí |
| **M4-sport − M4-cal** | **−0,00001 [−0,00006; +0,00004]** | **EQ** | sí |
| A − C | −0,01073 [−0,01194; −0,00952] | S-R | sí |

**Sensibilidad (T2, T3):** en las 13 comparaciones de la prueba interna y en las 2 decisiones de la
escalera (M2 frente a M1; H1b), la categoría es la misma con bloques de 2, 4, 8 y 12 semanas y con
ambas definiciones de semana. Los IC apenas cambian con el bloque (semanas calendario, de 2 a 12):
la semiamplitud de M4-sport − M4-cal va de ~5·10⁻⁵ a ~4,5·10⁻⁵ y la de M2 − A, de 8,0·10⁻⁴ a
8,5·10⁻⁴. La autocorrelación
semanal de Δ está entre −0,07 y +0,19 en los rezagos 1, 2 y 4. Es coherente con el bloque de 4 semanas
y está lejos del caso sintético extremo (φ = 0,7) en el que todo bloque infra-cubre (G7).

**Potencia en el holdout (T4; N = 15.154 de nivel 0; δ = 0,001; aproximación normal):**

| Comparación | se holdout | Superioridad: MDE frente a 0 | Superioridad: mejora real necesaria para S-R | Equivalencia: P(IC ⊂ (−δ, δ) \| θ = 0) | Equivalencia: mayor \|θ\| con potencia ≥ 80% |
|---|---|---|---|---|---|
| M4-sport − M4-cal | 4,9·10⁻⁵ | 1,4·10⁻⁴ | 1,14·10⁻³ | ≈ 1,00 | 8,6·10⁻⁴ |
| M4-sport − A | 1,3·10⁻⁴ | 3,6·10⁻⁴ | 1,36·10⁻³ | ≈ 1,00 | 6,4·10⁻⁴ |
| M4-cal − A | 1,2·10⁻⁴ | 3,3·10⁻⁴ | 1,33·10⁻³ | ≈ 1,00 | 6,7·10⁻⁴ |
| M2 − A | 8,5·10⁻⁴ | 2,4·10⁻³ | 3,39·10⁻³ | ≈ 0,00 | no alcanzable |

Lectura:
- Para las comparaciones de M4, el holdout tiene potencia para **demostrar equivalencia** si la
  diferencia real es pequeña (|θ| < ~6-9·10⁻⁴).
- Para declarar una **superioridad relevante** (S-R), la mejora real tendría que superar ~1,1·10⁻³.
  Con una diferencia real de 0, la equivalencia se demostraría casi con seguridad. No es lo mismo que
  detectar mejoras pequeñas.
- Para M2 − A, el holdout **no** puede demostrar equivalencia (se ≈ δ) y solo detectaría
  diferencias de ~2,4·10⁻³ o más.

## 4. Convergencia: los 226 casos, uno a uno (T7; `convergence_check_fits.csv`)

| Medida | Resultado |
|---|---|
| Casos verificados | 226 de 226 (164 cadenas configuración-bloque-división, reproducidas desde cero) |
| Cadenas con predicciones bit a bit iguales a las publicadas | 159 de 164; las 5 restantes son `M2__h480_r64_pp` (§2) |
| Casos que la reproducción vuelve a marcar no convergentes | 223. Los **3 no reproducidos** son de `M2__h480_r64_pp` (E2 2012-09-21, T1 2008-02-15, T1 2012-10-05): con otro orden de suma, esos ajustes cumplen el criterio |
| Gradiente residual de la solución publicada (223 casos reproducidos) | 9,7·10⁻⁷ a 2,0·10⁻⁵ (criterio de GATE 2: 10⁻⁸·Σw) |
| Tras pulir con Newton (criterio 10⁻¹⁰·Σw) | 226/226 lo alcanzan; gradiente 1,8·10⁻¹⁵ a 2,1·10⁻¹³ |
| f(θ publicado) − f(θ pulido) | entre −6,8·10⁻¹³ y 0: sin mejora del objetivo a precisión de máquina (f ~ 10³) |
| max\|Δθ\| | 7,7·10⁻⁸ |
| Filas predichas por esos ajustes | 1.800; \|Δp\| máx 2,7·10⁻⁸, medio 4,2·10⁻⁹ |
| Impacto en log loss | suma 3,4·10⁻⁷ nats; máx. sobre la log loss media de una configuración-bloque: 4,5·10⁻¹² |
| Casos no reproducibles | 3, todos explicados por el no determinismo de `_pp`; 0 casos sin pulir |

Conclusión: la marca "sin convergencia" era un artefacto del criterio de parada de Armijo cerca de la
precisión de máquina. Esta vez está **medido en los 226 casos**, no extrapolado.

## 5. Desviación D-3 (M3: forma lineal frente a log1p), solo en el bloque de ajuste (T6)
- Con log1p, M3 selecciona `GSTC_h15_r100`, la misma configuración que con la forma lineal.
- H1b con log1p: −0,00008 [−0,00028; +0,00013], EQ. Los tiros siguen fuera de M4-sport; decisión sin
  cambios.
- M3* log1p − M3* lineal: −0,00006 [−0,00013; +0,00002], EQ.
- La prueba interna **no** se reevaluó con log1p (para no añadir comparaciones post hoc). M3 no es
  candidato congelado, y M4-sport no usa M3.

## 6. Interpretación (exigencia 7)
- Lo que se puede decir: **en 2014/15-2021/22, con los modelos M1-M3 (goles, tiros, tiros a puerta y
  córners por EWMA) y con M4-sport definido por la desviación logit p_M2* − logit p_A, no se demostró
  información incremental sobre una recalibración del consenso de mercado pre-cierre (EQ).**
- Lo que no se puede decir: que la información deportiva en general carezca de valor; que otras
  variables (xG, alineaciones, lesiones), formulaciones u otros períodos fracasarían; o que la
  rentabilidad simulada sea negativa o positiva. Q3 se evalúa aparte, con la regla de selección y los
  precios observados.
- Todo lo anterior es **desarrollo**, no un veredicto. El veredicto formal exige GATE 3 (validación) y
  el holdout.

## 7. Paquetes de auditoría
- **ZIP ligero** (`python -m qsports audit-package --light`): código, pruebas, configuración,
  documentación, dependencias, muestra sintética y metadatos de nivel 0 necesarios para fallar
  cerrado; **sin Parquet** ni datos de la fuente o sellados. Construido desde `5add761` (0,73 MB, 254
  archivos). Probado por Claude en un entorno virtual limpio: 144 pruebas superadas y 15 omitidas
  (integración, sin datos de la fuente); `audit-synthetic` → `"ok": true`
  (`reports/gate2_1/TEST_RECORD.md`, A8).
- Paquete completo (`python -m qsports audit-package`): incluye además las predicciones publicadas.

## 8. Decisiones que necesito de ti
1. ¿Das por cerrada GATE 2.1 (correcciones, reproducción y desviaciones D-3 y D-4 documentadas)?
2. **No determinismo de `_pp`:** ¿autorizas la corrección de una línea (iterar `sorted(departed)`) antes
   de GATE 3? Solo afecta a configuraciones no seleccionadas; exigiría repetir la reproducción limpia
   para que corresponda al nuevo commit.
3. **GATE 3:** ¿autorizas la validación en 2022/23-2023/24 con los candidatos congelados (M4-sport
   h730 r1000 con X = desviación de M2*; M4-cal h730; M2*), una sola evaluación y la partición del
   protocolo §6? Si la autorizas, crearé `configs/gate3_frozen_candidates.json` y, con tu
   declaración expresa, `GATE3_AUTHORIZATION.json`. No crearé ninguno antes de tu respuesta.
4. ¿Fusionar `gate2.1` con `main`? (No lo haré sin tu indicación.)

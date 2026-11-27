# GATE_3_REPORT — Validación histórica 2022/23-2023/24 (una sola evaluación)

Fecha: 2026-11-27 · Rama: `gate3` (no fusionada con `main`) · Estado: **completado; me detengo antes de
GATE 4** · Holdout 2024/25-2025/26 y reserva 2026/27: **sellados, 0 accesos registrados**

Preregistro: `MODEL_SPECIFICATION.md` Parte C (commit `e2ac6da`, anterior a la evaluación). Resultados:
`experiments/gate3/validation_run/results.json`. Sello de evaluación única: `logs/GATE3_EVALUATED.json`.

## 1. Resumen

| Pregunta | Resultado en la validación 2022/23-2023/24 (n = 15.488) |
|---|---|
| ¿La desviación de M2 aporta información sobre el mercado recalibrado? (**comparación principal**) | **M4-sport − M4-cal = −0,000007 [−0,000129; +0,000111] → EQ.** Aporte incremental **no demostrado**, igual que en el desarrollo |
| ¿Los candidatos de mercado mejoran el consenso A? | M4-sport − A = −0,00042 [−0,00077; −0,00008] → **S-NR**; M4-cal − A = −0,00042 [−0,00075; −0,00008] → **S-NR**. Mejora estadística pequeña; su relevancia (> 0,001) **no está demostrada** |
| ¿De dónde viene esa mejora? | De la **recalibración** del consenso, no de la información deportiva. A estaba comprimido (pendiente de calibración 1,20); M4-cal la lleva a 1,06. M4-sport no añade nada a M4-cal (EQ) |
| ¿El modelo deportivo independiente iguala al mercado? | M2 − A = +0,00635 [+0,00486; +0,00798] → **I-R** (claramente peor) |
| Q2, condición de validez 1 (dirección de M4-sport − A) | Δ̄ = −0,00042 < 0 → **dirección consistente** |
| Q3 (rentabilidad simulada) | **NO EVALUADA**: no se congeló ninguna regla de selección de apuestas en el desarrollo (preregistro §C) |

Estos son resultados de **validación de desarrollo**, no veredictos de Q1-Q3, que se reservan al
holdout. **VENTAJA ESTADÍSTICA NO DEMOSTRADA** en sentido relevante: ninguna comparación frente al mercado
alcanza S-R.

## 2. Comprobaciones previas exigidas (todas superadas antes de evaluar)

| # | Exigencia | Evidencia |
|---|---|---|
| 1 | `sorted(departed)` en models.py, líneas 151 y 178 | Commit `ea5598d` |
| 2 | Prueba con distintos `PYTHONHASHSEED` | `tests/test_determinism.py`: semillas 0-3 (sintético con 5 ascensos y descensos) y 0-2 (datos reales, T1, M2 h480 r64 con prior). Con el código antiguo **ambas fallan** (prueba de mutación hecha); con la corrección, pasan |
| 3 | Reproducción limpia repetida; candidatos sin cambios | `experiments/gate3/repro_run` (`ea5598d`, `--clean`, árbol limpio, 2.362 s). Frente a la reproducción `a724e84`: 130 archivos y 8.472.766 filas; **los 6 archivos de los candidatos son idénticos bit a bit, con el mismo SHA-256**; decisiones y 13 comparaciones internas idénticas; única diferencia `M2__h480_r64_pp` (≤ 1,04·10⁻⁸, efecto de la corrección). `experiments/gate3/repro_comparison_vs_gate2_1.json` |
| 4 | El ejecutor verifica identidad e hiperparámetros | `qsports.gate3`: registro y selecciones de la referencia, argumentos completos del constructor, atributos instanciados, hash de código, SHA-256 de las entradas, protocolo. Además, **réplica de identidad**: los candidatos reconstruidos desde el archivo congelado reproducen bit a bit las 61.370 predicciones de la prueba interna de M2, M4-cal y M4-sport. `tests/test_gate3.py` (17 pruebas, con 11 manipulaciones detectadas) |
| 5 | Congelar M4-sport, M4-cal y M2; SESOI 0,001; protocolo vigente | `configs/gate3_frozen_candidates.json` (commit `e339fc6`); autorización ligada a su SHA-256 `a08152ce…` (commit `3bf3750`) |

## 3. Candidatos congelados
| Candidato | Configuración | Argumentos |
|---|---|---|
| M2* | `M2__h480_r64` | Poisson por división; semivida 480 d; ridge 64; historia máx. 1.460 d; sin prior de ascendidos; reajuste en cada captura |
| M4-cal* | `M4cal__h730` | logit p = a + b·logit p_A; semivida 730 d; reajuste cada 4 capturas |
| M4-sport* | `M4sport__h730_r1000` | M4-cal + β·(logit p_M2* − logit p_A); ridge 1.000 sobre β; semivida 730 d |

## 4. Resultados (bootstrap por bloques de 4 semanas calendario, 10.000 réplicas, semilla 20261127; δ = 0,001)

Cobertura: los tres candidatos cubren el 100% del universo (15.488 filas elegibles de 2022/23-2023/24;
0 faltantes). 99 semanas de calendario, 93 con partidos.

| Comparación | Δ̄ log loss | IC 95% | Categoría | DM p (HAC) | Δ Brier |
|---|---|---|:---:|---|---|
| **M4-sport − M4-cal** (principal) | −0,000007 | [−0,000129; +0,000111] | **EQ** | 0,913 | −0,000003 |
| M4-sport − A | −0,000425 | [−0,000769; −0,000080] | **S-NR** | 0,018 | −0,000201 |
| M4-cal − A | −0,000418 | [−0,000753; −0,000076] | **S-NR** | 0,018 | −0,000198 |
| M2 − A | +0,006351 | [+0,004857; +0,007980] | **I-R** | < 0,001 | +0,003086 |
| M2 − C | −0,008351 | [−0,010286; −0,006393] | **S-R** | < 0,001 | −0,004123 |
| A − C | −0,014703 | [−0,017572; −0,011946] | **S-R** | < 0,001 | −0,007209 |

Comparaciones secundarias con corrección de Holm (protocolo §6), sobre los p-valores de DM de las 5
secundarias: todas siguen siendo significativas al 5%. Los p ajustados de M4-sport − A y M4-cal − A son
≈ 0,036 (0,0179 × 2), y las tres restantes son < 0,001.

**Sensibilidad al bloque** (2, 4, 8 y 12 semanas calendario): **ninguna categoría cambia**. M4-sport −
M4-cal es EQ en los cuatro; M4-sport − A y M4-cal − A son S-NR en los cuatro; con 12 semanas, U = −0,00018
y −0,00020. La autocorrelación semanal de Δ está entre −0,11 y +0,15 (rezagos 1-4).

**Por temporada:**

| Comparación | 2022/23 | 2023/24 |
|---|---|---|
| M4-sport − M4-cal | +0,00008 | −0,00010 |
| M4-sport − A | −0,00035 | −0,00050 |
| M4-cal − A | −0,00044 | −0,00040 |
| M2 − A | +0,00455 | +0,00815 |

**Calibración y discriminación:**

| Pronóstico | Log loss | Brier | Pendiente | Intercepto en grande | ECE | AUC |
|---|---|---|---|---|---|---|
| A (consenso pre-cierre) | 0,67445 | 0,24080 | **1,202** | 0,020 | 0,0148 | 0,6098 |
| M4-cal | 0,67403 | 0,24061 | 1,058 | 0,020 | 0,0086 | 0,6097 |
| M4-sport | 0,67403 | 0,24060 | 1,057 | 0,019 | 0,0111 | 0,6097 |
| M2 | 0,68080 | 0,24389 | 1,068 | 0,074 | 0,0186 | 0,5910 |
| C | 0,68915 | 0,24801 | 1,080 | 0,097 | 0,0266 | 0,5556 |

Lectura: M4-cal y M4-sport tienen **la misma discriminación que A** (AUC 0,6097 frente a 0,6098). Su
ventaja procede de corregir la compresión de A (pendiente 1,20 → 1,06), no de ordenar mejor los partidos.

**Convergencia:** M2, 1.962 ajustes y 1 marcado no convergente (F2, 2022-07-29, gradiente 1,03·10⁻⁵, máx.
de iteraciones). Es el mismo artefacto del criterio de parada que los 226 casos de GATE 2, verificados en
GATE 2.1. **No se repitió** para no volver a tocar la validación. M4-cal y M4-sport: 43 ajustes cada uno,
0 no convergentes.

## 5. Desarrollo frente a validación

| Comparación | Prueba interna 2014/15-2021/22 | Validación 2022/23-2023/24 |
|---|---|---|
| M4-sport − M4-cal | −0,00001 [−0,00006; +0,00004] EQ | −0,00001 [−0,00013; +0,00011] EQ |
| M4-cal − A | −0,00008 [−0,00019; +0,00004] EQ | −0,00042 [−0,00075; −0,00008] S-NR |
| M4-sport − A | −0,00009 [−0,00021; +0,00004] EQ | −0,00042 [−0,00077; −0,00008] S-NR |
| M2 − A | +0,00480 I-R | +0,00635 I-R |
| Pendiente de calibración de A | 1,103 | 1,202 |

El aporte deportivo sigue sin demostrarse. Lo que cambia es la ganancia de recalibrar el mercado: en la
validación el consenso A está más comprimido (pendiente 1,20 frente a 1,10). Por eso la recalibración
(M4-cal) mejora a A de forma detectable, aunque por debajo de δ.

## 6. Interpretación (alcance limitado)
- **Sí puede decirse:** en 2022/23-2023/24, con estos candidatos congelados, (a) la desviación de M2*
  respecto del mercado no aporta información distinguible sobre M4-cal (EQ, de nuevo); (b) recalibrar
  el consenso pre-cierre lo mejora de forma estadísticamente detectable pero pequeña (S-NR, < δ); (c) el
  modelo Poisson independiente es claramente peor que el mercado.
- **No puede decirse:** que exista una ventaja relevante frente al mercado (ninguna comparación alcanza
  S-R); que la mejora por recalibración genere rentabilidad (Q3 no evaluada; una mejora de 0,0004 nats en
  log loss no implica beneficio tras el margen); nada sobre otras variables, modelos o períodos; ni un
  veredicto de Q2, que requiere el holdout y las tres condiciones de validez.
- **Etiqueta:** VENTAJA ESTADÍSTICA NO DEMOSTRADA (relevante). La mejora de M4-sport sobre A es S-NR y se
  explica por la recalibración.

## 7. Protección e integridad
- **Registro de la valla:** 4 cruces "allowed": M2, M4-cal y M4-sport en el motor, más el universo de
  evaluación. Todos con la autorización vigente; 0 rechazados.
- **`verify`:** ok, 0/0 accesos registrados al holdout y a la reserva, que siguen sellados.
- **Evaluación única:** `logs/GATE3_EVALUATED.json` (SHA-256 de `results.json` = `f0046440…`). Un segundo
  intento lo rechaza `SingleEvaluationError`.
- **Sin cambios:** ningún modelo ni variable nuevos, ni el mercado, las fuentes o el protocolo. No se
  fusionó con `main`.

## 7b. Pruebas y paquete (ejecutados por Claude; el auditor no los ha ejecutado aún)
- `pytest` formal en `a27897a`: **178 superadas, 0 fallos** (`experiments/gate3/records/pytest_a27897a.*`).
  En `2e04fca` hubo 3 fallos: pruebas de la valla dependientes del estado, ya con autorización real.
  Se corrigieron haciéndolas herméticas; el registro fallido se conserva.
- ZIP ligero de GATE 3 (`dist/audit_package_gate3_light.zip`, 0,95 MB, sin Parquet), probado en un
  entorno limpio: 162 superadas, 16 omitidas (integración); `audit-synthetic` → `"ok": true`.
- Manifiesto de hashes: `experiments/gate3/records/HASH_MANIFEST_GATE3.json`. El hash del código actual
  sigue siendo igual al congelado.

## 8. Decisiones para ti (me detengo antes de GATE 4)
1. ¿Apruebas GATE 3 con estos resultados?
2. **Q3:** ¿quieres definir y congelar una regla de selección de apuestas simulada (umbral de EV, tope de
   cuota, apuesta fija, casa de referencia) **antes** del holdout? Debería fijarse sin mirar la validación
   con ese fin, o asumir que Q3 no se evaluará.
3. **Candidato primario para el holdout:** el protocolo exige uno solo (condición de validez 3). Con
   esta evidencia, M4-sport y M4-cal son prácticamente iguales; elegir M4-cal sería lo coherente con lo
   observado, pero es tu decisión y debe quedar congelada antes de GATE 4.
4. ¿Autorizas GATE 4 (auditoría del modelo y congelamiento del protocolo)? No haré nada hasta tu
   respuesta.

# Tablas de GATE 2.1 (generadas por experiments/gate2_1/build_tables.py)

Fuente: `experiments/gate2_1/repro_run/results.json` (ejecución limpia) y `experiments/gate2/results.json` (publicado). n = 61.137 filas en la prueba interna.

## T1. Prueba interna: método publicado (semanas activas) frente a método corregido (semanas calendario), bloque 4

| Comparación | Δ̄ | IC publicado | Cat. | IC reproducido, mismo método | Cat. | IC calendario (principal) | Cat. |
|---|---|---|---|---|---|---|---|
| M1-C | -0,00520 | [-0,00597; -0,00442] | S-R | [-0,00597; -0,00442] | S-R | [-0,00595; -0,00443] | **S-R** |
| M2-C | -0,00593 | [-0,00677; -0,00510] | S-R | [-0,00677; -0,00510] | S-R | [-0,00676; -0,00509] | **S-R** |
| M3-C | -0,00519 | [-0,00584; -0,00450] | S-R | [-0,00584; -0,00450] | S-R | [-0,00583; -0,00452] | **S-R** |
| M1-A | +0,00553 | [+0,00465; +0,00640] | I-R | [+0,00465; +0,00640] | I-R | [+0,00464; +0,00640] | **I-R** |
| M2-A | +0,00480 | [+0,00398; +0,00562] | I-R | [+0,00398; +0,00562] | I-R | [+0,00394; +0,00562] | **I-R** |
| M3-A | +0,00554 | [+0,00462; +0,00649] | I-R | [+0,00462; +0,00649] | I-R | [+0,00460; +0,00646] | **I-R** |
| M2-M1 | -0,00073 | [-0,00098; -0,00047] | S-NR | [-0,00098; -0,00047] | S-NR | [-0,00099; -0,00048] | **S-NR** |
| M3-M2 | +0,00075 | [+0,00017; +0,00133] | I-NR | [+0,00017; +0,00133] | I-NR | [+0,00016; +0,00131] | **I-NR** |
| M4cal-A | -0,00008 | [-0,00020; +0,00004] | EQ | [-0,00020; +0,00004] | EQ | [-0,00019; +0,00004] | **EQ** |
| M4sport-A | -0,00009 | [-0,00022; +0,00004] | EQ | [-0,00022; +0,00004] | EQ | [-0,00021; +0,00004] | **EQ** |
| M4sport-M4cal | -0,00001 | [-0,00006; +0,00004] | EQ | [-0,00006; +0,00004] | EQ | [-0,00006; +0,00004] | **EQ** |
| A-C | -0,01073 | [-0,01198; -0,00953] | S-R | [-0,01198; -0,00953] | S-R | [-0,01194; -0,00952] | **S-R** |
| Freq730-C | -0,00039 | [-0,00097; +0,00018] | EQ | [-0,00097; +0,00018] | EQ | [-0,00095; +0,00016] | **EQ** |

## T2. Sensibilidad al bloque (2, 4, 8, 12 semanas) y a la definición de semana

| Comparación | Δ̄ | calendario 2 | 4 | 8 | 12 | activas 2 | 4 | 8 | 12 | Categorías | ACF semanal r1, r2, r4 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M1-C | -0,00520 | [-0,00594; -0,00445] S-R | [-0,00595; -0,00443] S-R | [-0,00601; -0,00436] S-R | [-0,00603; -0,00439] S-R | [-0,00594; -0,00444] S-R | [-0,00597; -0,00442] S-R | [-0,00599; -0,00438] S-R | [-0,00603; -0,00440] S-R | S-R | +0,05, +0,03, +0,14 |
| M2-C | -0,00593 | [-0,00673; -0,00513] S-R | [-0,00676; -0,00509] S-R | [-0,00681; -0,00502] S-R | [-0,00682; -0,00506] S-R | [-0,00671; -0,00511] S-R | [-0,00677; -0,00510] S-R | [-0,00679; -0,00505] S-R | [-0,00680; -0,00507] S-R | S-R | +0,07, +0,03, +0,11 |
| M3-C | -0,00519 | [-0,00583; -0,00453] S-R | [-0,00583; -0,00452] S-R | [-0,00585; -0,00448] S-R | [-0,00588; -0,00449] S-R | [-0,00584; -0,00452] S-R | [-0,00584; -0,00450] S-R | [-0,00585; -0,00450] S-R | [-0,00586; -0,00450] S-R | S-R | -0,00, +0,01, +0,05 |
| M1-A | +0,00553 | [+0,00470; +0,00638] I-R | [+0,00464; +0,00640] I-R | [+0,00457; +0,00639] I-R | [+0,00459; +0,00639] I-R | [+0,00471; +0,00639] I-R | [+0,00465; +0,00640] I-R | [+0,00460; +0,00638] I-R | [+0,00458; +0,00638] I-R | I-R | +0,11, +0,04, +0,07 |
| M2-A | +0,00480 | [+0,00401; +0,00561] I-R | [+0,00394; +0,00562] I-R | [+0,00389; +0,00561] I-R | [+0,00390; +0,00559] I-R | [+0,00402; +0,00561] I-R | [+0,00398; +0,00562] I-R | [+0,00390; +0,00560] I-R | [+0,00389; +0,00561] I-R | I-R | +0,11, +0,04, +0,08 |
| M3-A | +0,00554 | [+0,00466; +0,00646] I-R | [+0,00460; +0,00646] I-R | [+0,00453; +0,00645] I-R | [+0,00455; +0,00645] I-R | [+0,00469; +0,00644] I-R | [+0,00462; +0,00649] I-R | [+0,00452; +0,00644] I-R | [+0,00454; +0,00643] I-R | I-R | +0,12, +0,05, +0,11 |
| M2-M1 | -0,00073 | [-0,00099; -0,00047] S-NR | [-0,00099; -0,00048] S-NR | [-0,00100; -0,00047] S-NR | [-0,00100; -0,00047] S-NR | [-0,00099; -0,00048] S-NR | [-0,00098; -0,00047] S-NR | [-0,00099; -0,00047] S-NR | [-0,00100; -0,00047] S-NR | S-NR | +0,08, -0,04, +0,05 |
| M3-M2 | +0,00075 | [+0,00020; +0,00130] I-NR | [+0,00016; +0,00131] I-NR | [+0,00013; +0,00134] I-NR | [+0,00015; +0,00135] I-NR | [+0,00020; +0,00130] I-NR | [+0,00017; +0,00133] I-NR | [+0,00014; +0,00133] I-NR | [+0,00015; +0,00135] I-NR | I-NR | +0,12, +0,03, +0,05 |
| M4cal-A | -0,00008 | [-0,00020; +0,00004] EQ | [-0,00019; +0,00004] EQ | [-0,00018; +0,00004] EQ | [-0,00018; +0,00003] EQ | [-0,00019; +0,00004] EQ | [-0,00020; +0,00004] EQ | [-0,00019; +0,00004] EQ | [-0,00018; +0,00003] EQ | EQ | -0,02, +0,01, -0,06 |
| M4sport-A | -0,00009 | [-0,00022; +0,00003] EQ | [-0,00021; +0,00004] EQ | [-0,00020; +0,00004] EQ | [-0,00020; +0,00003] EQ | [-0,00021; +0,00003] EQ | [-0,00022; +0,00004] EQ | [-0,00020; +0,00004] EQ | [-0,00020; +0,00003] EQ | EQ | -0,02, -0,00, -0,07 |
| M4sport-M4cal | -0,00001 | [-0,00006; +0,00004] EQ | [-0,00006; +0,00004] EQ | [-0,00005; +0,00004] EQ | [-0,00005; +0,00004] EQ | [-0,00006; +0,00004] EQ | [-0,00006; +0,00004] EQ | [-0,00005; +0,00004] EQ | [-0,00005; +0,00004] EQ | EQ | -0,05, +0,07, +0,02 |
| A-C | -0,01073 | [-0,01191; -0,00959] S-R | [-0,01194; -0,00952] S-R | [-0,01199; -0,00939] S-R | [-0,01199; -0,00940] S-R | [-0,01188; -0,00961] S-R | [-0,01198; -0,00953] S-R | [-0,01193; -0,00942] S-R | [-0,01195; -0,00942] S-R | S-R | +0,14, +0,05, +0,10 |
| Freq730-C | -0,00039 | [-0,00094; +0,00015] EQ | [-0,00095; +0,00016] EQ | [-0,00099; +0,00023] EQ | [-0,00098; +0,00022] EQ | [-0,00095; +0,00015] EQ | [-0,00097; +0,00018] EQ | [-0,00099; +0,00022] EQ | [-0,00098; +0,00022] EQ | EQ | +0,04, +0,08, +0,19 |

## T3. Decisiones de la escalera (bloque de ajuste) según bloque y definición de semana

| Decisión | Filas (modo, bloque → IC, categoría, U < 0) | ¿Estable? |
|---|---|---|
| M2_vs_M1 | cal 2: [-0,00081; -0,00034] S-NR sí; act 2: [-0,00081; -0,00033] S-NR sí; cal 4: [-0,00080; -0,00033] S-NR sí; act 4: [-0,00080; -0,00035] S-NR sí; cal 8: [-0,00080; -0,00033] S-NR sí; act 8: [-0,00080; -0,00035] S-NR sí; cal 12: [-0,00081; -0,00034] S-NR sí; act 12: [-0,00080; -0,00034] S-NR sí | sí |
| H1b_shots_vs_goals | cal 2: [-0,00024; +0,00018] EQ no; act 2: [-0,00023; +0,00017] EQ no; cal 4: [-0,00024; +0,00018] EQ no; act 4: [-0,00024; +0,00018] EQ no; cal 8: [-0,00025; +0,00017] EQ no; act 8: [-0,00025; +0,00017] EQ no; cal 12: [-0,00027; +0,00018] EQ no; act 12: [-0,00026; +0,00015] EQ no | sí |

## T4. Potencia en el holdout: superioridad frente a equivalencia (δ = 0,001)

N elegible (nivel 0) = 15.154. se_holdout = se_bootstrap_desarrollo · sqrt(n_desarrollo / n_holdout) (semanas calendario, bloque 4); aproximación normal. Superioridad y equivalencia por separado.

| Comparación | se desarrollo | se holdout | MDE superioridad vs 0 | Mejora real necesaria para S-R | P(IC ⊂ (−δ, δ) si θ = 0) | Máx. θ con equivalencia al 80% | se necesario para equivalencia |
|---|---|---|---|---|---|---|---|
| M4sport-M4cal | 2,43e-05 | 4,89e-05 | 1,37e-04 | 1,14e-03 | 1,000 | 8,63e-04 | 3,08e-04 |
| M4sport-A | 6,38e-05 | 1,28e-04 | 3,59e-04 | 1,36e-03 | 1,000 | 6,41e-04 | 3,08e-04 |
| M4cal-A | 5,91e-05 | 1,19e-04 | 3,33e-04 | 1,33e-03 | 1,000 | 6,67e-04 | 3,08e-04 |
| M2-A | 4,25e-04 | 8,53e-04 | 2,39e-03 | 3,39e-03 | 0,000 | — | 3,08e-04 |

## T5. Cobertura del universo de la prueba interna

| Pronóstico | Esperadas | Cubiertas | Faltantes | Sobrantes |
|---|---|---|---|---|
| A | 61.137 | 61.137 | 0 | 233 |
| C | 61.137 | 61.137 | 0 | 233 |
| Freq730 | 61.137 | 61.137 | 0 | 233 |
| M1 | 61.137 | 61.137 | 0 | 233 |
| M2 | 61.137 | 61.137 | 0 | 233 |
| M3 | 61.137 | 61.137 | 0 | 233 |
| M4cal | 61.137 | 61.137 | 0 | 233 |
| M4sport | 61.137 | 61.137 | 0 | 233 |

## T6. Sensibilidad D-3 (M3 con log(1 + partidos previos), solo bloque de ajuste)

- M3 seleccionado con log1p: `M3log__GSTC_h15_r100` (lineal: `M3__GSTC_h15_r100`; misma configuración salvo la transformación: sí).
- H1b con log1p (tiros frente a goles): -0,00008 [-0,00028; +0,00013] EQ → los tiros entran en M4-sport: no (con la forma lineal: no; decisión sin cambios: sí).
- M3* log1p − M3* lineal (bloque de ajuste): -0,00006 [-0,00013; +0,00002] EQ.

## T7. Verificación de los ajustes no convergentes

- Ajustes no convergentes publicados: 226; verificados uno a uno: 226 (164 cadenas configuración-bloque-división).
- Cadenas con predicciones idénticas bit a bit a las publicadas: 159/164; con el mismo conjunto de ajustes no convergentes: 161/164.
- Criterio estricto: max|grad| <= 1e-10·max(1, Σw)  (GATE 2: 1e-8·max(1, Σw)). Alcanzado en 226/226.
- Gradiente residual de la solución publicada (casos reproducidos, n = 223): 9,74e-07-2,01e-05; tras pulir (226 casos): 1,78e-15-2,14e-13.
- f(θ publicado) − f(θ estricto): mín -6,82e-13, mediana -1,14e-13, máx 0,00e+00; max|Δθ| = 7,71e-08.
- Filas predichas por esos ajustes: 1.800; |Δp| máx = 2,72e-08, medio = 4,19e-09.
- Impacto en log loss: suma total 3,44e-07 nats; máximo impacto en la log loss media de una configuración-bloque: 4,48e-12 nats.
- Casos no reproducibles o no pulidos: 3.

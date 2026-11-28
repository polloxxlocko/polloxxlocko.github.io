# FINAL_EXPERIMENT_REPORT — Informe definitivo del experimento

**Quantitative Sports Intelligence · Fútbol, Over/Under 2,5 goles prepartido · 22 divisiones de
Football-Data.co.uk** · Fecha: 2026-11-28 · Rama `final` (no fusionada con `main`)

Prueba final ejecutada **una sola vez** sobre el holdout 2024/25-2025/26, con el protocolo congelado v1.1
(hash `9c81e30189ba6732106873810f75140e79b71a3ac2152589d8f65421c601e63f`) y M4-cal h730 como candidato
primario único. Resultados completos: `experiments/final/holdout_run/results.json` (SHA-256
`a8a0d3a2…aef7`). Reserva 2026/27: **sellada, 0 accesos**.

## 0. Veredictos formales

| Pregunta | Comparación | Δ̄ log loss [IC 95%] | Categoría | Veredicto |
|---|---|---|:---:|---|
| **Q1**: ¿mejora a una referencia estadística simple? | M4-cal − C (frecuencia histórica) | **−0,013835 [−0,016962; −0,011030]** | **S-R** | **AFIRMATIVO**: mejora relevante sobre una referencia simple |
| **Q2**: ¿mejora las probabilidades del mercado? | M4-cal − A (consenso pre-cierre sin margen) | **+0,000057 [−0,000292; +0,000381]** | **EQ** | **VENTAJA ESTADÍSTICA NO DEMOSTRADA** (equivalencia práctica; las tres condiciones de validez se cumplen, pero la categoría no es S-R ni S-NR) |
| **Q3**: ¿genera rentabilidad simulada? | — | — | — | **NO EVALUADA** (protocolo económico separado, solo simulado) |

**Conclusión principal (resultado negativo para Q2).** En el holdout, el modelo congelado es
**prácticamente equivalente** al consenso del mercado. El IC queda dentro de ±0,0004 nats, muy por debajo
del umbral de relevancia δ = 0,001, y no hay superioridad ni estadística ni relevante. La pequeña ventaja
de recalibración observada en la validación 2022/23-2023/24 (S-NR) **no se replicó**.

## 1. Pregunta y diseño (resumen)
- **Misión:** investigar *si* existe ventaja predictiva, no demostrarla. Las preguntas son tres y
  separadas: Q1 frente a referencias simples, Q2 frente al mercado, Q3 rentabilidad simulada.
- **Mercado (GATE 0):** Over/Under 2,5 prepartido, tiempo reglamentario. **Datos:** Football-Data.co.uk,
  22 divisiones, 2000/01-2025/26. **Particiones:**
  - desarrollo ≤ 2023/24 (ajuste 2005/06-2013/14, prueba interna 2014/15-2021/22, validación
    2022/23-2023/24);
  - holdout 2024/25-2025/26, sellado;
  - reserva ≥ 2026/27, sellada.
- **Benchmarks:** A = consenso promedio pre-cierre normalizado (proporcional); C = frecuencia histórica de
  Over por división, point-in-time.
- **Point-in-time estricto:** cada predicción usa solo información anterior a su fecha de captura
  (walk-forward; pruebas de invariancia al futuro).
- **Escalera de modelos (GATE 2):** M1/M2 Poisson, M3 logística con goles/tiros/córners, M4-cal
  (recalibración del mercado) y M4-sport (M4-cal + desviación de M2). M5 no se justificó.
- **Desviaciones aceptadas:** D-1 a D-4 (grilla, optimizador, forma de M3, semanas calendario).
- **Candidato primario (decisión del usuario tras GATE 3):** M4-cal h730, logit p = a + b·logit p_A con
  pesos de semivida 730 días, reajuste cada 4 capturas. Es una recalibración del mercado **sin
  información deportiva**.

## 2. Trayectoria de la evidencia

| Comparación | Prueba interna 2014/15-2021/22 | Validación 2022/23-2023/24 (GATE 3) | **Holdout 2024/25-2025/26** |
|---|---|---|---|
| M4-cal − A | −0,00008 [−0,00019; +0,00004] EQ | −0,00042 [−0,00075; −0,00008] S-NR | **+0,00006 [−0,00029; +0,00038] EQ** |
| M4-cal − C | −0,0108 (desarrollo) | (A − C: −0,0147 S-R) | **−0,0138 [−0,0170; −0,0110] S-R** |
| M4-sport − M4-cal (información deportiva) | −0,00001 EQ | −0,00001 EQ | no evaluado (no era candidato primario) |
| M2 (modelo deportivo) − A | +0,0048 I-R | +0,0064 I-R | no evaluado |
| Pendiente de calibración de A | 1,103 | 1,202 | **1,039** |
| Pendiente de calibración de M4-cal | 1,003 | 1,058 | **0,922** |

**Lectura de la trayectoria:**
- **La información deportiva** (desviación de M2) no aportó nada distinguible sobre el mercado recalibrado
  en el desarrollo ni en la validación. El modelo deportivo independiente fue claramente peor que el
  mercado.
- **La recalibración del consenso** solo dio una mejora detectable en 2022/23-2023/24, cuando el consenso
  estaba especialmente comprimido (pendiente 1,20).
- **En el holdout** el consenso estuvo mejor calibrado (pendiente 1,04). M4-cal, que aprendió del pasado
  una expansión b ≈ 1,16, sobre-expandió ligeramente (pendiente 0,92). Resultado: ninguna ganancia (EQ).

## 3. Prueba final: ejecución y controles
| Control | Resultado |
|---|---|
| Autorización | `HOLDOUT_AUTHORIZATION.json` con la declaración literal del usuario, ligado al hash `9c81e301…` (commit `bb2f3d6`, anterior a la ejecución) |
| Identidad | Código `20071ecc…`; candidato y M2 auxiliar = GATE 3; entradas con el SHA-256 congelado; réplica de identidad bit a bit (61.370 de 61.370 filas en M2 y en M4-cal) |
| Dataset de desarrollo | Contenido `41d9503c…f5b9` y benchmarks `c2b1dd65…42e5`: iguales a los autorizados |
| Holdout cargado | 15.328 filas; hash de contenido `b859bdab…e592` = registro = especificación congelada |
| Benchmarks recalculados (desarrollo + holdout) | Idénticos a los almacenados en todas las filas de desarrollo |
| Estados (`logs/FINAL_TEST_STATE_LOG.jsonl`) | `started` 02:50:45.97 → `opened` 02:50:47.15 → `finished` 02:50:59.42 (UTC) |
| Marcador y sello | `logs/FINAL_TEST_ATTEMPT.json` (exclusivo, persistente) y `logs/FINAL_TEST_EVALUATED.json` |
| Valla | 3 usos `allowed-holdout` (M2 auxiliar, M4-cal, universo), todos con la autorización vigente; 0 rechazados |
| Archivos congelados | Sin cambios: el hash del protocolo tras la ejecución sigue siendo `9c81e301…` |

## 4. Resultados completos

**Universo:** 15.154 partidos (temporadas 2024/25 y 2025/26, resultado conocido, captura estimable,
`elig_A`). Coincide con la estimación de nivel 0 previa. Cobertura de M4-cal: **100%**. Hay 174
predicciones fuera del universo (filas no elegibles), que no se evalúan. 97 semanas de calendario, 90 con
partidos.

| | Q1: M4-cal − C | Q2: M4-cal − A |
|---|---|---|
| Δ̄ log loss | −0,013835 | +0,000057 |
| IC 95% (bloques de 4 semanas calendario, 10.000 réplicas, semilla 20261127) | [−0,016962; −0,011030] | [−0,000292; +0,000381] |
| Error estándar bootstrap | 1,51·10⁻³ | 1,69·10⁻⁴ |
| Categoría (δ = 0,001) | **S-R** | **EQ** |
| Superioridad estadística (U < 0) | sí | **no** |
| Superioridad relevante (U < −δ) | sí | **no** |
| Rentabilidad | NO EVALUADA | NO EVALUADA |
| Diebold-Mariano (HAC) | t = −8,93; p = 4,2·10⁻¹⁹ | t = +0,33; p = 0,744 |
| Δ Brier | −0,006766 | +0,000032 |
| Log loss (modelo / referencia) | 0,679240 / 0,693076 | 0,679240 / 0,679184 |
| Efecto de diseño semanal | 1,16 | 1,10 |

**Sensibilidad al bloque** (semanas calendario; informativa, no cambia la decisión):

| Bloque | Q1 IC | Q1 | Q2 IC | Q2 |
|---|---|---|---|---|
| 2 | [−0,01667; −0,01115] | S-R | [−0,00028; +0,00039] | EQ |
| **4 (principal)** | [−0,01696; −0,01103] | S-R | [−0,00029; +0,00038] | EQ |
| 8 | [−0,01682; −0,01121] | S-R | [−0,00024; +0,00028] | EQ |
| 12 | [−0,01669; −0,01136] | S-R | [−0,00021; +0,00022] | EQ |

**Por temporada:**

| | 2024/25 | 2025/26 |
|---|---|---|
| M4-cal − C | −0,01488 | −0,01277 |
| M4-cal − A | +0,00011 | +0,000004 |

**Calibración, discriminación y nitidez** (n = 15.154; frecuencia observada de Over 0,5145):

| Pronóstico | Log loss | Brier | Pendiente | Intercepto en grande | ECE | AUC | p media | sd(p) |
|---|---|---|---|---|---|---|---|---|
| M4-cal | 0,67924 | 0,24319 | 0,922 | 0,012 | 0,0094 | 0,5913 | 0,5115 | 0,0882 |
| A | 0,67918 | 0,24316 | 1,039 | 0,022 | 0,0100 | 0,5913 | 0,5091 | 0,0790 |
| C | 0,69308 | 0,24995 | 0,596 | 0,096 | 0,0347 | 0,5307 | 0,4908 | 0,0449 |

**Condiciones de validez de Q2** (protocolo §6):
1. Dirección en la validación (−0,000418 < 0): **cumplida**.
2. Calibración en el holdout: |0,922 − 1| = 0,078 < 0,2 y |0,012| < 0,05. **Cumplida**.
3. Modelo primario único: **cumplida**.

Aun así, la categoría es EQ, de modo que el veredicto es **VENTAJA ESTADÍSTICA NO DEMOSTRADA**.

**Ajustes:**
- M4-cal: 42 ajustes, 0 no convergentes.
- M2 auxiliar: 1.959 ajustes, 5 marcados no convergentes. Es el artefacto conocido del criterio de parada.
  M4-cal solo usa la *disponibilidad* de `inp_m2`, que no depende de la convergencia.

**Frente a la potencia preregistrada** (`FINAL_TEST_PROTOCOL.md` §8):
- Si la diferencia real fuera 0, se esperaba EQ con probabilidad 0,95.
- Si fuera la de GATE 3 (−0,00042), se esperaba S-NR con 0,67 y EQ con 0,33.
- Se observó EQ, con la estimación puntual a favor del mercado.

## 5. Interpretación
- **Q1 (afirmativo):** M4-cal supera ampliamente a la frecuencia histórica por división (−0,0138 nats, S-R,
  estable por temporada y por bloque). Esto refleja sobre todo **la información contenida en las cuotas del
  mercado**: M4-cal es una recalibración del consenso, y A − C tuvo una magnitud similar en la validación.
  No es una prueba de habilidad deportiva propia.
- **Q2 (negativo):** con el protocolo preregistrado, M4-cal **no mejora** las probabilidades del consenso
  pre-cierre. La equivalencia práctica sí está demostrada: el IC [−0,00029; +0,00038] cae entero dentro de
  ±δ. La ventaja observada en la validación fue específica de ese período.
- **Alcance de la conclusión negativa:** se limita a lo evaluado:
  - mercado O/U 2,5 prepartido;
  - las 22 divisiones de Football-Data;
  - el consenso promedio pre-cierre como referencia;
  - información de goles, tiros y córners y cuotas pre-cierre;
  - los modelos M1-M4 y sus formulaciones, en los períodos indicados.

  No demuestra que sea imposible mejorar al mercado con otra información (xG, alineaciones, lesiones),
  otros modelos u otros mercados.
- **Q3:** no evaluada. La equivalencia en log loss frente al consenso **sin margen** no dice nada directo
  sobre la rentabilidad, ni positiva ni negativa. Las cuotas reales incluyen el margen (~6%) y la regla de
  selección no se definió.
- **Etiquetas:** `VENTAJA ESTADÍSTICA NO DEMOSTRADA` (Q2). Para la rentabilidad: no evaluada.

## 6. Integridad, desviaciones e incidente
- **Cadena de preregistro:**
  - protocolo de GATE 1;
  - preregistro de GATE 2 (MODEL_SPECIFICATION Parte A);
  - D-1 a D-4 aceptadas;
  - preregistro de GATE 3 (Parte C, commit `e2ac6da`, anterior a la validación);
  - congelamiento de GATE 4 (`fd8685f1…`), sustituido por GATE 4.1 (`9c81e301…`) solo para controles de
    ejecución;
  - autorización (`bb2f3d6`);
  - ejecución (02:50 UTC) y resultados (`49971c7`).
- **Reserva 2026/27:** sellada, 0 accesos.
- **Exposición previa:** la exposición de nivel 1 de la Fase Cero sigue documentada
  (`HOLDOUT_PROTECTION_PROTOCOL.md` §5). "Accesos registrados" no equivale a ausencia absoluta de exposición.
- **Incidente I-1 (acceso no evaluativo posterior al sellado).**
  - *Qué pasó:* a las 02:53:00 UTC, unos dos minutos después del sello de la evaluación (02:50:59), Claude
    ejecutó `pytest` para cerrar la tarea. Una prueba antigua, `test_open_reserved_denied_in_current_project_state`,
    suponía el holdout sellado. Con la autorización ya vigente, la apertura tuvo éxito y quedó registrada en
    `data/holdout/ACCESS_LOG.jsonl` con propósito `"test"`.
  - *Alcance:* los datos se cargaron en memoria y se descartaron. No se calcularon predicciones, métricas ni
    salidas. La prueba falló y no se usó nada. La evaluación ya estaba sellada (hash de `results.json` en el
    sello), así que **no pudo verse afectada**.
  - *Causa:* error de proceso de Claude. Protegió el ejecutor final, pero no revisó las pruebas que dependen
    del estado del proyecto.
  - *Corrección (solo pruebas, ningún archivo congelado):*
    - guarda en `tests/conftest.py` que impide a cualquier prueba abrir datos reservados reales;
    - pruebas dependientes del estado convertidas en herméticas;
    - 218 superadas y registros sin cambios después.
  - La entrada del registro **no se borró ni se editó**. El holdout tiene 2 accesos registrados: la
    evaluación y este incidente.
- **`verify` tras la apertura:** los 13 controles de integridad son verdaderos. `ok = false` solo porque el
  holdout ya no está sellado, que es lo esperado tras la apertura autorizada.

## 7. Reproducibilidad
- **Sin datos sellados:**
  - código, pruebas, protocolo, especificación, registros y resultados agregados están en la rama `final`;
  - el ZIP ligero permite verificar hashes, el protocolo congelado y la lógica del ejecutor con datos
    sintéticos.
- **Con los datos de la fuente:** el desarrollo se reconstruye con `python -m qsports download` + `build`.
  La evaluación del holdout no debe repetirse (evaluación única). Las predicciones del holdout están en
  `experiments/final/holdout_run/` (`predictions_M4cal.parquet`, `predictions_M2_aux.parquet`), con sus
  hashes en `results.json`.

## 8. Comprobaciones independientes
El auditor (ChatGPT) verificó GATE 1, GATE 2, GATE 2.1, GATE 3, GATE 4 y GATE 4.1: hashes de paquetes,
archivos congelados, hash del protocolo, potencia, resolución de los hallazgos A y B y pruebas
seleccionadas sin PyArrow. Su `pytest` completo no pudo certificarse por la falta de PyArrow en su entorno.
Detalle en `experiments/gate4/records/INDEPENDENT_AUDIT_RECORD.md`. **La prueba final y sus pruebas
posteriores las ejecutó Claude.** El auditor aún no ha revisado estos resultados.

## 9. Estado
Experimento confirmatorio **concluido**. El holdout 2024/25-2025/26 ya no es independiente: ningún modelo,
parámetro o regla posterior puede evaluarse en él. La reserva 2026/27 sigue sellada. **No se inicia ninguna
nueva línea de investigación** sin una decisión expresa del usuario. Eso incluye el protocolo económico
separado de Q3.

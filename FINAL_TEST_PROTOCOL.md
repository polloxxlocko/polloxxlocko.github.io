# FINAL_TEST_PROTOCOL — Protocolo congelado de la prueba final (holdout 2024/25-2025/26)

Versión 1.1 · Congelado en GATE 4 (2026-11-28) y vuelto a congelar en GATE 4.1 (2026-11-28) con dos controles
de ejecución añadidos (§1 y §2). No cambian el modelo, los hiperparámetros, el SESOI, el universo, la estadística
ni los criterios de decisión. Forma parte de `PROTOCOL_FREEZE.json`: cualquier cambio en este documento invalida la
autorización de apertura.

Especificación ejecutable: `configs/final_test_frozen.json`. Ejecutor: `qsports.final_test`
(`experiments/final/run_final.py run --out DIR`).

## 1. Autoridad y evaluación única
- El holdout (temporadas 2024/25 y 2025/26) solo puede abrirse con `HOLDOUT_AUTHORIZATION.json`. Ese
  archivo se crea únicamente por instrucción expresa del usuario y debe estar ligado al hash de
  `PROTOCOL_FREEZE.json`.
- La reserva (2026/27 en adelante) no se abre en este protocolo: el motor la rechaza incluso con la
  autorización del holdout.
- **Una sola evaluación.** El ejecutor se niega si existe cualquiera de estos tres:
  - el directorio de salida;
  - el sello `logs/FINAL_TEST_EVALUATED.json`;
  - el **marcador de intento** `logs/FINAL_TEST_ATTEMPT.json` (GATE 4.1).
- **Marcador de intento.** Se crea de forma exclusiva (O_CREAT | O_EXCL, con fsync) **inmediatamente antes de
  abrir el holdout** y nunca se borra automáticamente. Por eso:
  - una interrupción posterior a la apertura (error, Ctrl-C, caída del proceso) no permite un segundo
    intento automático;
  - tampoco lo permite una ejecución concurrente.

  Los errores detectados **antes** de abrir (autorización, identidad, hash del desarrollo, hash del
  registro) no crean el marcador. Retomar la prueba tras una interrupción exigiría una decisión explícita
  del usuario, que quedaría documentada.
- **Registro de estados** append-only `logs/FINAL_TEST_STATE_LOG.jsonl`: `started` (marcador creado, antes
  de abrir), `opened` (holdout cargado y hash verificado), `finished` (resultados y sello escritos) e
  `interrupted` (cualquier excepción tras el inicio, con su tipo). Una muerte abrupta del proceso puede no
  dejar `interrupted`, pero el marcador sigue impidiendo el reintento.
- Tras abrirse, el holdout deja de ser independiente: ningún modelo, parámetro o regla posterior puede
  evaluarse en él.
- Se informa todo, sea cual sea el resultado.

## 2. Datos autorizados (hashes en `configs/final_test_frozen.json`)
- **Desarrollo:** dataset procesado con hash de contenido `41d9503c…f5b9` (182.821 filas) y benchmarks
  `c2b1dd65…42e5`. El ejecutor los recalcula al cargar y se detiene si no coinciden.
- **Holdout:** hash de contenido sellado `b859bdab…e592`, congelado en la especificación
  (`dataset.holdout_full_content_sha256_sealed`). GATE 4.1 refuerza tres comprobaciones:
  - al verificar la especificación y **antes de abrir**, el hash del registro debe ser igual al congelado;
  - **tras cargar**, el hash de contenido del holdout debe coincidir **a la vez** con el registro y con la
    especificación congelada;
  - si el dataset y el registro coinciden entre sí pero no con la especificación, se rechaza.

  También constan el hash de nivel 0 y el SHA-256 de cada ZIP RAW.
- **Benchmarks del holdout:** A (consenso pre-cierre sin margen, normalización proporcional) y C
  (frecuencia histórica point-in-time). Se recalculan con el mismo código sobre desarrollo + holdout. En
  las filas de desarrollo deben coincidir exactamente con los almacenados.

## 3. Candidato primario único (seleccionado por el usuario tras GATE 3)
**M4-cal h730** (`M4cal__h730`), idéntico al congelado y evaluado en GATE 3:
- **Modelo:** logit p = a + b·logit p_A, con p_A recortado a [10⁻⁶, 1 − 10⁻⁶] (el recorte no actúa en
  el desarrollo).
- **Estimación:** máxima verosimilitud bernoulli ponderada con pesos w = 2^(−edad/730 días) respecto de
  la fecha de ajuste τ. Sin penalización sobre (a, b), por lo que el argumento ridge = 100 es inerte.
  L-BFGS-B con gtol = 10⁻⁷, máximo 2.000 iteraciones y arranque en caliente desde el ajuste anterior.
- **Filas de entrenamiento en τ:** partidos con fecha anterior a τ que tengan p_A, resultado e `inp_m2`
  disponible. `inp_m2` solo define el subconjunto; su valor no interviene. Con menos de 200 filas,
  predicción NaN.
- **Reajuste:** cada 4 fechas de captura, conjunto para todas las divisiones. Predicción solo con p_A.
- **`inp_m2`:** predicción fuera de muestra de M2* (Poisson por división, semivida 480 d, ridge 64,
  historia máx. 1.460 d, sin prior de ascendidos). Desarrollo 2005/06-2023/24: archivos congelados de
  GATE 2-3 (SHA-256 en la especificación). Holdout: M2* walk-forward con cadena propia desde la primera
  captura de 2024/25. M2* es **auxiliar** (disponibilidad); no se evalúa.

## 4. Controles de identidad (antes de cargar el holdout)
1. Hash del código igual al congelado.
2. Archivos de modelo (`models.py`, `odds.py`, `ou.py`, `benchmark.py`) iguales a los de GATE 3.
3. Candidato y auxiliar idénticos (dict completo) a los del archivo congelado de GATE 3, con el mismo
   SHA-256.
4. Atributos de los modelos instanciados iguales a los congelados.
5. Entradas con el SHA-256 congelado.
6. Réplica de identidad: M2* y M4-cal, reconstruidos desde la especificación, deben reproducir bit a bit
   las 61.370 predicciones de la prueba interna de desarrollo.

## 5. Universo de evaluación
Temporadas 2024/25 y 2025/26, con resultado conocido, captura estimable y `elig_A`: par promedio válido
con margen en [0; 0,25], captura no ambigua y sin clave duplicada. M4-cal debe cubrir el 100% del
universo; si falta una predicción, la evaluación se detiene. Tamaño estimado por el conteo de nivel 0:
15.154 partidos.

## 6. Estadística (congelada)
- **Medida:** Δ = log loss(M4-cal) − log loss(referencia), por partido; Δ̄ < 0 significa que M4-cal es
  mejor.
- **IC 95%:** bootstrap percentil por bloques móviles de **4 semanas calendario** (incluye las semanas sin
  partidos), 10.000 réplicas, semilla 20261127.
- **δ (SESOI) = 0,001 nats.**
- **Partición** (`EXPERIMENTAL_PROTOCOL.md` §6, excluyente):
  - S-R: U < −δ
  - S-NR: −δ ≤ U < 0
  - EQ: L ≤ 0 ≤ U, con L > −δ y U < δ
  - INC: L ≤ 0 ≤ U, con L ≤ −δ o U ≥ δ
  - I-NR: 0 < L ≤ δ
  - I-R: L > δ
- **Se informan sin cambiar la decisión:** bloques de 2, 4, 8 y 12 semanas; Δ por temporada; calibración
  (pendiente e intercepto en grande); Brier; Diebold-Mariano con HAC.

## 7. Preguntas y veredictos
- **Q1 (M4-cal − C):**

  | Categoría | Veredicto |
  |---|---|
  | S-R | AFIRMATIVO, mejora relevante sobre una referencia simple |
  | S-NR | AFIRMATIVO, mejora estadística de magnitud incierta |
  | EQ, I-NR, I-R | NEGATIVO |
  | INC | EVIDENCIA INSUFICIENTE |

- **Q2 (M4-cal − A):** AFIRMATIVO solo con S-R o S-NR **y** las tres condiciones de validez:
  1. Dirección consistente en la validación: Δ̄(M4-cal − A) en GATE 3 = −0,000418 < 0. **Cumplida.**
  2. Calibración aceptable en el holdout: |pendiente − 1| < 0,2 y |intercepto en grande| < 0,05.
  3. Un único modelo primario declarado al congelar. **Cumplida.**

  En cualquier otro caso: **VENTAJA ESTADÍSTICA NO DEMOSTRADA**, indicando la categoría y la condición que
  falle. Si la categoría es INC: VENTAJA ESTADÍSTICA NO DEMOSTRADA / EVIDENCIA INSUFICIENTE.
- **Q3 (rentabilidad simulada): NO EVALUADA** en este experimento confirmatorio. Se investigará después
  con un protocolo separado y exclusivamente simulado.
- **Lectura obligatoria:**
  - superioridad estadística (U < 0) ≠ superioridad relevante (U < −δ) ≠ rentabilidad (no evaluada);
  - una mejora de log loss no implica beneficio tras el margen.

## 8. Expectativa de potencia (con los resultados de GATE 3; `experiments/gate4/power_gate3.json`)
- se esperado de Δ(M4-cal − A) en el holdout: 1,75·10⁻⁴.
- MDE de superioridad frente a 0: 4,9·10⁻⁴. Mejora real necesaria para S-R con potencia del 80%: 1,49·10⁻³.
- Si la diferencia real fuese la de GATE 3 (−0,00042): P(S-NR) = 0,67, P(EQ) = 0,33, P(S-R) ≈ 0. Si fuese 0:
  P(IC ⊂ (−δ, δ)) = 0,9998.
- Q1: la mejora necesaria para S-R es 4,7·10⁻³, y en el desarrollo la diferencia observada fue −0,0108.
  P(S-R) ≈ 1 si la diferencia real es como la de A − C en GATE 3.

## 9. Fuera de alcance
Modelos, variables, mercados o fuentes nuevos; cambios de hiperparámetros, de reglas de reajuste o del
universo; comparaciones adicionales con categoría de decisión; reserva; Q3.

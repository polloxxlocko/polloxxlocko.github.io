# MODEL_AUDIT_REPORT — GATE 4: auditoría de M4-cal y congelamiento de la prueba final

Fecha: 2026-11-28 · Rama `gate4` (no fusionada con `main`) · Estado: **completado; me detengo y solicito
autorización expresa para abrir el holdout** · Holdout 2024/25-2025/26 y reserva 2026/27: **sellados,
0 accesos registrados**

| Elemento congelado | Valor |
|---|---|
| Commit del congelamiento | `20af512` |
| Hash del protocolo (`PROTOCOL_FREEZE.json`, 39 archivos) | `fd8685f1413cf94348538a6f5ca79024da82481d69026334bd6f8ea8ee3592d0` |
| Especificación ejecutable | `configs/final_test_frozen.json` |
| Hash del código congelado | `f380539ce5a5ebc52c1ffef65519eadb91b69061253d92cfed84aa162e9af179` |
| Candidato primario único | **M4-cal h730** (`M4cal__h730`), idéntico al de GATE 3 |
| Dataset de desarrollo autorizado | contenido `41d9503c…f5b9` (182.821 filas); benchmarks `c2b1dd65…42e5` |
| Holdout autorizado (hash sellado, sin abrir) | contenido `b859bdab…e592`; nivel 0 `8f841a5e…38b9`; ZIP 2024/25 `4dc3abfd…f0de`, 2025/26 `0cf572ed…fa66`; 15.328 partidos en el registro |

## 1. Resumen
- **M4-cal se auditó** en su formulación matemática, en su implementación (8 pruebas nuevas) y en su
  comportamiento empírico. No apareció ningún defecto que altere sus predicciones. Hallazgos
  documentados:
  - el argumento ridge es inerte;
  - M4-cal depende de M2* solo para definir sus filas de entrenamiento (10 de 146.585 filas
    excluidas);
  - el recorte de p_A no actúa;
  - 0 de 385 ajustes no convergentes.
- **Ajuste no convergente de GATE 3:** documentado sin repetir la evaluación. Se reproduce exactamente
  con datos anteriores a τ, su pulido cambia p en ≤ 2,3·10⁻⁸ y no afecta a M4-cal.
- **Potencia reestimada con GATE 3:**
  - si la diferencia real fuese la de GATE 3 (−0,00042), el holdout daría S-NR con probabilidad 0,67 y
    EQ con 0,33;
  - **S-R exige una mejora real ≥ 1,5·10⁻³**;
  - si no hay diferencia real, la equivalencia se demostraría con probabilidad 0,9998.
- **Ejecutor de la prueba final preparado:**
  - controles de identidad, de hash de los datos y de evaluación única;
  - probado **solo con datos sintéticos** (14 pruebas);
  - ensayado con datos reales **de desarrollo** (sin el holdout): identidad bit a bit y hashes correctos;
  - sin autorización se niega antes de cargar nada; probado, y el registro de accesos sigue vacío.
- **Protocolo congelado** (`FINAL_TEST_PROTOCOL.md`). Q3 queda **NO EVALUADA**, por decisión del usuario.

## 2. Formulación matemática de M4-cal
Para la fecha de ajuste τ y las filas i de entrenamiento (fecha < τ, con p_A, resultado y `inp_m2`
disponibles):

  ℓ(a, b) = Σ_i w_i · [ log(1 + e^{η_i}) − y_i·η_i ],  con  η_i = a + b·logit(p_A,i)  y  w_i = 2^(−(τ − fecha_i)/730)

(â, b̂) = argmin ℓ. Predicción: p = 1 / (1 + e^{−(â + b̂·logit p_A)}).

Propiedades:
- **Convexidad.** ℓ es convexa porque la hessiana Xᵀ·diag(w·μ(1−μ))·X es semidefinida positiva. Si las
  columnas (1, logit p_A) no son colineales y los datos no son separables, el óptimo es único.
- **Interpretación.** Es la regresión de calibración de Cox: b > 1 indica un consenso comprimido hacia
  0,5, que hay que expandir; b < 1, uno demasiado extremo; a corrige un sesgo global. No incorpora
  información deportiva.
- **Pesos.** La semivida es de 730 días. En τ = 2024-08-02, el tamaño efectivo de muestra es 44.259 y el
  50,3% del peso recae en los dos últimos años.
- **Sin penalización.** El vector de penalización vale 0 para a y b, así que el argumento ridge = 100 de la
  configuración no interviene; se demuestra en `test_ridge_inert_for_m4cal`.

## 3. Auditoría de la implementación (`src/qsports/models.py`, `MarketModel`, `fit_logistic`)

| # | Aspecto | Comprobación | Resultado |
|---|---|---|---|
| A1 | Gradiente analítico | `check_grad` con pesos | error < 10⁻⁵ |
| A2 | Optimizador (L-BFGS-B, gtol 10⁻⁷) | Frente a un solver IRLS independiente | Coeficientes a ≤ 2·10⁻⁶; objetivo no peor (relativo 10⁻⁷) |
| A3 | Recuperación | 200.000 filas sintéticas con a = 0,05 y b = 1,2 | Recuperados dentro de ±0,02 / ±0,03 |
| A4 | Pesos | Dos copias a 731 días equivalen a una a 1 día | Igualdad del ajuste (10⁻⁵); control distinto |
| A5 | `inp_m2` | Cambiar sus valores, con el mismo patrón de disponibilidad | Predicciones idénticas bit a bit; un patrón distinto cambia la muestra (control) |
| A6 | ridge | ridge = 1 frente a 10⁶ | Coeficientes idénticos bit a bit |
| A7 | Muestra insuficiente y fórmula de predicción | Menos de 200 filas → NaN; fórmula logística | Correcto (10⁻¹⁵) |
| A8 | Recorte de p_A | Rango en el desarrollo | 0,237-0,861: el recorte [10⁻⁶, 1−10⁻⁶] no actúa |
| A9 | Point-in-time | Invariancia al futuro e independencia del lote (GATE 2) | Superadas (`test_models.py`) |
| A10 | Identidad | Reconstrucción desde la especificación congelada | 61.370 predicciones internas iguales bit a bit |

**Hallazgo H1: dependencia de M2*.**
- `require_cols = ["inp_m2"]` hace que las filas de entrenamiento de M4-cal dependan de que M2* tenga
  predicción. En 2005/06-2023/24 hay 146.585 filas con p_A y resultado; solo 10 quedan fuera por esa
  máscara (divisiones sin historia previa). Las filas anteriores a 2005/06 nunca entran.
- Para conservar **exactamente** la configuración evaluada, el ejecutor final corre M2* como auxiliar en
  el holdout. Sus valores no afectan a M4-cal (A5).

**Hallazgo H2: estabilidad.**
- (a, b) en 385 ajustes (2006-2024): a ∈ [−0,090; 0,015] y b ∈ [1,004; 1,234]. Mediana de b por
  temporada: 1,09-1,11 en 2018/19-2022/23 y 1,15 en 2023/24. Último ajuste antes del holdout: b = 1,156.
- La compresión del consenso persiste pero varía: es el riesgo principal (`LIMITATIONS.md` F2).

## 4. Comportamiento observado (resultados ya publicados, no reevaluados)
| Bloque | M4-cal − A | Categoría | Pendiente de A → M4-cal |
|---|---|---|---|
| Prueba interna 2014/15-2021/22 | −0,00008 [−0,00019; +0,00004] | EQ | 1,10 → 1,00 |
| Validación 2022/23-2023/24 (GATE 3) | −0,00042 [−0,00075; −0,00008] | S-NR | 1,20 → 1,06 |

En la validación, M4-cal tiene la misma discriminación que A (AUC 0,6097 frente a 0,6098). Su ventaja es
de calibración.

## 5. Ajuste no convergente de GATE 3 (sin repetir la evaluación)
`experiments/gate4/gate3_nonconverged_fit.json`:
- **Reproducción:** F2, τ = 2022-07-29, primer ajuste de la cadena (arranque en frío). Se reconstruye
  solo con partidos anteriores a τ: 8.260, igual que en el registro. Reproduce exactamente el mensaje
  publicado (`gmax=1.03e-05 max_iter`).
- **Pulido** con Newton hasta 10⁻¹⁰·Σw: gradiente 9,2·10⁻¹⁴; f(publicado) − f(pulido) = −4,5·10⁻¹³ (sin
  mejora a precisión de máquina); max|Δθ| = 3,7·10⁻⁸.
- **Efecto:** |Δp| máximo sobre los 1.056 cruces posibles de equipos es 2,3·10⁻⁸. No se usaron filas ni
  resultados de la validación.
- **M4-cal:** sin efecto, porque solo usa la disponibilidad de `inp_m2`.

## 6. Potencia para el holdout (con GATE 3; `experiments/gate4/power_gate3.json`)
N elegible (nivel 0) = 15.154; se(holdout) = se_bootstrap(GATE 3) · √(15.488 / 15.154).

| Q2: M4-cal − A | Valor |
|---|---|
| se esperado | 1,75·10⁻⁴ (con el desarrollo sería 1,19·10⁻⁴; GATE 3 es más conservador) |
| MDE superioridad estadística (U < 0) | 4,9·10⁻⁴ |
| Mejora real necesaria para superioridad **relevante** (S-R), potencia 80% | 1,49·10⁻³ |
| Equivalencia: P(IC ⊂ (−δ, δ) \| θ = 0) | 0,9998; potencia ≥ 80% mientras \|θ\| < 5,1·10⁻⁴ |

| Diferencia real θ | P(S-R) | P(S-NR) | P(EQ) |
|---|---|---|---|
| 0 | 0,00 | 0,025 | 0,95 |
| −0,00042 (estimación de GATE 3) | 0,00 | 0,67 | 0,33 |
| −0,001 (= δ) | 0,025 | 0,97 | 0,00 |
| −0,0015 | 0,81 | 0,19 | 0,00 |

Q1 (M4-cal − C): el se esperado es 1,3·10⁻³ y S-R exige una mejora real de 4,7·10⁻³. La diferencia en el
desarrollo fue −0,0108 (A − C en GATE 3: −0,0147), así que P(S-R) ≈ 1 si se mantiene.

**Superioridad estadística, superioridad relevante y rentabilidad son cosas distintas:**
- S-NR significa que M4-cal es mejor que A más allá del azar, pero sin poder afirmar que supere δ;
- solo S-R sería relevante;
- ninguna de las dos dice nada sobre la rentabilidad (Q3 no evaluada).

## 7. Congelamiento (`PROTOCOL_FREEZE.json`, hash `fd8685f1…`)
Archivos congelados (39):
- `EXPERIMENTAL_PROTOCOL.md` (v1.0), `FINAL_TEST_PROTOCOL.md`, `MARKET_BENCHMARK_SPECIFICATION.md`;
- los 8 `configs/*.json`, incluidos `final_test_frozen.json` y `gate3_frozen_candidates.json`;
- los 25 módulos de `src/qsports`;
- `experiments/final/run_final.py`, `requirements-lock.txt` y `pyproject.toml`.

Contenido congelado:
- **Código:** todo `src/qsports` y el ejecutor.
- **Configuración e hiperparámetros:** M4-cal (semivida 730 d, reajuste cada 4 capturas, L-BFGS-B) y M2*
  auxiliar (480 d, ridge 64, 1.460 d, sin prior).
- **Requisitos de datos:** p_A, resultado e `inp_m2` para el entrenamiento; p_A para predecir.
- **Universo:** `elig_A`.
- **Protocolo estadístico:** bloques de 4 semanas calendario, 10.000 réplicas, semilla, δ = 0,001.
- **Veredictos:** Q1, Q2 (con sus tres condiciones) y Q3 no evaluada.

`tests/test_protocol_freeze.py` comprueba que ningún archivo congelado cambia y que el hash es estable.

## 8. Ejecutor de la prueba final (`qsports.final_test`)
Orden de ejecución:
1. Guardas de evaluación única.
2. **Autorización del holdout** (si no hay, se detiene sin cargar nada).
3. Verificación de la especificación: código, archivos de modelo, candidato = GATE 3, atributos y
   entradas.
4. Hash del dataset de desarrollo.
5. Réplica de identidad bit a bit.
6. Carga del holdout con registro de acceso.
7. **Hash de contenido sellado.**
8. Benchmarks recalculados, que deben ser idénticos en el desarrollo.
9. M2* auxiliar y M4-cal en walk-forward con la autorización, verificada en cada llamada.
10. Evaluación con cobertura del 100%: Q1, Q2 con condiciones y Q3 no evaluada.
11. Sello.

Pruebas, todas con datos sintéticos salvo la negativa en modo real:
- de extremo a extremo;
- rechazo sin autorización antes de cargar;
- hash del holdout alterado;
- hash del desarrollo alterado;
- réplica de identidad alterada en 10⁻¹²;
- tablas de veredictos;
- niveles de superioridad;
- negativa en modo real sin registrar accesos;
- identidad de la especificación congelada frente a 5 manipulaciones.

## 9. Comprobaciones independientes frente a las de Claude
Detalle en `experiments/gate4/records/INDEPENDENT_AUDIT_RECORD.md`.
- **El auditor (ChatGPT), sobre el ZIP de `25944d9`:**
  - 414/414 hashes;
  - 141 pruebas superadas, 16 omitidas, y 8 fallos y 13 errores atribuidos a la falta de PyArrow en su
    entorno;
  - `audit-synthetic` ok;
  - hashes del código congelado, de los resultados y de la autorización de GATE 3 verificados;
  - categorías consistentes, registros vacíos y 4 cruces autorizados.
- **Claude** ejecutó por su cuenta las 178 pruebas de `a27897a` y las 162 del ZIP. No se atribuyen al
  auditor.
- **PyArrow:** está declarado en `requirements-lock.txt` y `pyproject.toml`. Desde GATE 4, `pytest` se
  detiene con un mensaje claro si falta.

## 10. Limitaciones y riesgos
Ver `LIMITATIONS.md` (F1-F4, V1-V4, G7-G12). Los principales:
- con la potencia esperada, la relevancia (S-R) de Q2 es casi inalcanzable si la mejora real se parece a
  la de GATE 3;
- la ventaja de M4-cal es de calibración y puede cambiar;
- el hash del holdout solo se comprueba al abrirlo;
- "0 accesos registrados" no equivale a la ausencia demostrada de exposición
  (`HOLDOUT_PROTECTION_PROTOCOL.md` §5).

## 11. Solicitud
Me detengo aquí. Para abrir el holdout necesito una **autorización expresa**. Con ella crearía
`HOLDOUT_AUTHORIZATION.json` ligado al hash del protocolo `fd8685f1…` y ejecutaría **una sola vez**
`python experiments/final/run_final.py run --out experiments/final/holdout_run`. Cualquier cambio en un
archivo congelado antes de la apertura exigiría un nuevo congelamiento y una nueva autorización.

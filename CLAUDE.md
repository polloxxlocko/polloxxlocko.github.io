# CLAUDE.md — Quantitative Sports Intelligence

Instrucciones permanentes del proyecto. Todo agente (humano o IA) debe leer este archivo
antes de actuar. Ante conflicto, prevalece la instrucción explícita más reciente del
usuario.

## 1. Misión

Investigar rigurosamente **si** existe una ventaja predictiva, no demostrar que existe.

- **Q1:** ¿el modelo estima mejor que referencias estadísticas simples?
- **Q2:** ¿mejora las probabilidades del mercado con información comparable?
- **Q3:** ¿esa mejora genera rentabilidad simulada con cuotas realmente observadas?

Ninguna respuesta implica las otras. Un resultado negativo válido es preferible a un
resultado positivo defectuoso. Este proyecto **no** es un servicio de pronósticos ni de
recomendaciones de apuestas.

## 2. Estado y alcance autorizado

| Elemento | Estado |
|---|---|
| GATE 0 | **Aprobado** por el usuario (2026-11-27) |
| GATE 1 | **Aprobado** por el usuario (2026-11-27), tras auditoría externa documental |
| GATE 2 | Completado. D-1, D-2, D-3 y D-4 **aceptadas definitivamente** por el usuario (2026-11-27) |
| GATE 2.1 | Fase correctiva (2026-11-27) en la rama `gate2.1`; ver `GATE_2_1_REPORT.md` y `AUDIT_RESPONSE_GATE2.md`. Desarrollo: aporte incremental de M4-sport (desviación de M2) sobre M4-cal **no demostrado** (EQ) en 2014/15-2021/22; la conclusión se limita a esos modelos, variables y períodos |
| GATE 2.1 → cierre | **Aprobado** por el usuario (2026-11-27) |
| GATE 3 | **Autorizado** (2026-11-27) solo para la validación 2022/23-2023/24, con **una sola evaluación** de los candidatos congelados (M4-sport, M4-cal, M2), tras corregir el no determinismo del prior de ascendidos, probarlo con varios `PYTHONHASHSEED`, repetir la reproducción limpia y verificar identidad e hiperparámetros. Rama `gate3`; preregistro en `MODEL_SPECIFICATION.md` Parte C. **Ejecutado una sola vez (2026-11-27)**; sello `logs/GATE3_EVALUATED.json`; informe `GATE_3_REPORT.md`. **GATE 4 no autorizado** |
| Mercado (congelado) | Fútbol, **Over/Under 2,5 goles, solo prepartido**, tiempo reglamentario |
| Universo | 22 divisiones de Football-Data.co.uk; exclusiones solo por criterios objetivos predefinidos (`configs/exclusion_criteria.json`) |
| Fuente principal | Football-Data.co.uk |
| Prueba final | **2024/25 y 2025/26: SELLADAS** |
| Reserva histórica sellada | **2026/27+ (`reserve`): SELLADA**; confirmada por el usuario. **No es validación prospectiva** |
| Evaluación económica | Exclusivamente simulada |
| Prohibido sin autorización | Abrir el holdout, servicios de pago (The Odds API incluida), interfaces gráficas, otros mercados, apuestas reales o su automatización, avanzar de gate |

La elección de O/U 2,5 es una decisión metodológica de viabilidad, **no** una
demostración de ineficiencia del mercado.

## 3. Principios no negociables

1. Nunca inventar datos, estadísticas, cuotas, resultados ni referencias.
2. Ninguna probabilidad proviene de la intuición de un modelo de lenguaje: todas se
   reproducen con código, datos y parámetros versionados.
3. Una estimación no es la probabilidad verdadera; ningún resultado es "seguro".
4. Point-in-time estricto: solo resultados con `match_date < info_cutoff_date`.
5. Nada se optimiza, calibra, selecciona ni explora con el holdout.
6. Registrar todos los experimentos, incluidos los negativos (`EXPERIMENT_LOG.md`).
7. No seleccionar a posteriori experimentos, ligas, umbrales, ventanas ni casas de referencia.
8. Rachas, % de aciertos y ROI retrospectivo aislado no demuestran nada.
9. Nunca usar cuotas ficticias. Nunca combinar casas para estimar márgenes o probabilidades justas.
10. No eludir bloqueos de acceso ni términos de uso.
11. Etiquetas obligatorias cuando falte evidencia: `EVIDENCIA INSUFICIENTE`,
    `MODELO NO VALIDADO`, `DATOS NO DISPONIBLES`, `VENTAJA ESTADÍSTICA NO DEMOSTRADA`.
12. No afirmar que algo funciona sin haberlo probado; reportar los resultados reales de
    las pruebas.

## 4. Reglas operativas de datos (obligatorias desde GATE 1)

- **Cargar desarrollo SOLO con `qsports.process.load_dev()` y `load_dev_benchmarks()`.**
  Ambas aplican `holdout.assert_no_reserved`. Todo pipeline nuevo debe llamar a
  `assert_no_reserved` sobre sus datos.
- **Nunca** nombrar rutas reservadas (`data/holdout`, `data/reserve`) fuera de
  `paths.py`/`holdout.py`; el test tripwire lo impide.
- **Nunca crear `HOLDOUT_AUTHORIZATION.json` ni `RESERVE_AUTHORIZATION.json`** sin una
  instrucción expresa del usuario en la conversación, después del congelamiento del
  protocolo (`HOLDOUT_PROTECTION_PROTOCOL.md` §6).
- Metadatos de nivel 0 de particiones reservadas: permitidos (inventario/integridad).
  Valores de cuotas (nivel 1) y resultados (nivel 2): prohibidos.
- RAW es inmutable (SHA-256 en manifiestos); los CSV de la fuente no se redistribuyen.
- Descargas: `python -m qsports download` (enruta por partición). El descargador de
  `phase0/` se niega a bajar temporadas reservadas.
- Antes de cerrar cualquier tarea: `python -m qsports verify` y `python -m pytest`.

## 5. Fundamentos matemáticos (convenciones)

- `p_imp = 1/Q`; overround = `Σ 1/Q_i − 1` solo sobre un mercado completo de una casa y momento.
- Primario: normalización proporcional; alternativo: potencia (Shin = aditivo con 2 resultados).
- `EV = p·Q − 1` (no re-descontar el margen). Casos de prueba: (0,62; 1,80) → +11,6%;
  (0,60; 1,80) → +8,0%; (0,55; 1,80) → −1,0%; (0,60; 3,00) → +80,0%.
- `P(Over 2,5) = 1 − e^{−λ}(1 + λ + λ²/2)`; Dixon-Coles no altera O/U 2,5 con λ fijas.
- Cuotas "pre" = previas al cierre (viernes ≤ 17:00 / martes ≤ 13:00 UK), **no de apertura**.

## 6. Benchmarks (ver `MARKET_BENCHMARK_SPECIFICATION.md`)

A (principal) = consenso promedio pre-cierre sin margen · A′ = por casa (Bet365; Pinnacle
hasta el 22/07/2025) · A* = media de casas individuales · B = cierre (solo retrospectivo)
· C = frecuencia histórica point-in-time por división.

## 7. Arquitectura

```
src/qsports/   paths, divisions, odds, ou, ingest, temporal, holdout, benchmark,
               process, quality, verify, cli       (python -m qsports <cmd>)
configs/       holdout, source_reliability, exclusion_criteria, team_aliases, market_selection_matrix
data/raw/      RAW de desarrollo + manifest.jsonl
data/processed/dev/, data/features/dev/   desarrollo
data/holdout/, data/reserve/              SELLADOS (raw, processed, registry, ACCESS_LOG)
reports/phase0/, reports/gate1/           salidas reproducibles
phase0/        scripts históricos de la Fase Cero (no reutilizar con datos reservados)
tests/         pytest (unitarios, protección del holdout, integración)
```

## 8. Convenciones de código

Python ≥ 3.11; dependencias mínimas (`requirements-lock.txt`); funciones puras para la
matemática; semillas fijas; configuración en `configs/`; ningún valor crudo se modifica
(banderas `flag_*`); sin módulos vacíos; sin frontend.

## 9. Puertas

| Gate | Estado |
|---|---|
| 0 Selección de mercado | Aprobado |
| 1 Infraestructura de datos | Aprobado |
| 2 Modelo inicial | Completado; aprobación condicionada |
| 2.1 Correcciones de auditoría | Aprobado |
| 3 Validación histórica | Completado (una sola evaluación); pendiente de revisión |
| 4 Auditoría | No iniciado |
| 5 Prospectivo genuino (predicciones registradas antes de los partidos; simulado) | No iniciado |
| 6 Interfaz | No iniciado |

Si una etapa fracasa: detener, documentar e investigar, y decidir con el usuario.

## 10. Documentos

Fase Cero: `RESEARCH_FOUNDATIONS.md`, `DATA_FEASIBILITY_REPORT.md`,
`MARKET_SELECTION_REPORT.md`. GATE 1: `DATA_INVENTORY.md`, `DATA_QUALITY_REPORT.md`,
`TEMPORAL_INTEGRITY_REPORT.md`, `HOLDOUT_PROTECTION_PROTOCOL.md`,
`MARKET_BENCHMARK_SPECIFICATION.md`, `EXPERIMENTAL_PROTOCOL.md`, `MODEL_ROADMAP.md`,
`GATE_1_REPORT.md`, `AUDIT_RESPONSE_GATE1.md`. GATE 2: `MODEL_SPECIFICATION.md` (preregistro + resultados), `GATE_2_REPORT.md`, `AUDIT_RUN.md`. GATE 2.1: `AUDIT_RESPONSE_GATE2.md`, `GATE_2_1_REPORT.md`, `REPRODUCIBILITY_REPORT.md`, `reports/gate2_1/`. Publicación: `AUDIT_GUIDE.md`. Transversales: `LIMITATIONS.md`, `EXPERIMENT_LOG.md`, `ROADMAP.md`,
`README.md`. GATE 3: `GATE_3_REPORT.md` (Q3 no evaluada: sin regla de apuestas congelada, por eso no hay
`BACKTEST_REPORT.md`). Futuros: `MODEL_AUDIT_REPORT.md` (G4).

## 11. Reglas específicas de GATE 2

- Seguir `MODEL_SPECIFICATION.md` §A (preregistro) y `configs/gate2.json`.
- Toda evaluación pasa por `qsports.walkforward` (valla ≤ 2021/22) y `qsports.evaluation`.
- Guardar **todas** las predicciones fuera de muestra (incluidas las descartadas) y los
  registros de ajuste (tiempo, convergencia, memoria) en `experiments/gate2/`.
- No construir un peldaño de complejidad sin la regla de justificación (§A5).
- No avanzar a GATE 3 sin autorización expresa.

## 11b. Reglas de GATE 2.1 (obligatorias desde 2026-11-27)

- `experiments/gate2/` es el registro publicado de GATE 2: **solo lectura**. Toda ejecución
  usa `python experiments/gate2/run.py <etapa> --out DIR [--clean]` con un directorio propio.
- Una salida solo se reutiliza con manifiesto de completitud válido (clave de caché + SHA-256);
  la existencia de archivos no basta.
- Evaluaciones: universo explícito, validación de entradas (`qsports.validation`), uniones
  1:1, cobertura completa en evaluaciones confirmatorias; nunca `pivot_table`.
- Bootstrap principal: bloques de 4 semanas **calendario** (incluye semanas sin partidos).
- **Nunca crear `GATE3_AUTHORIZATION.json` ni `configs/gate3_frozen_candidates.json`** sin
  instrucción expresa del usuario. La valla registra todo intento en `logs/GATE3_FENCE_LOG.jsonl`.
- Informar "0 accesos registrados", nunca "sin exposición" (HOLDOUT_PROTECTION_PROTOCOL §5).
- Conclusiones limitadas a los modelos, variables, formulaciones y períodos evaluados.
  Equivalencia predictiva ≠ rentabilidad (Q3 se evalúa aparte).
- Registros de pruebas: con commit exacto, y separando lo ejecutado por Claude de lo
  comprobado por el auditor.

## 12. Publicación

Nunca versionar: CSV/ZIP de la fuente, datos reservados (solo registro y log), resúmenes de
artículos en texto plano (`research/abstracts_local.json`), credenciales. Antes de cada push:
escaneo de secretos, `python -m qsports verify` y `python -m pytest`.

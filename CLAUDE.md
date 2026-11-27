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
| GATE 1 | **Completado, pendiente de revisión del usuario** (ver `GATE_1_REPORT.md`) |
| GATE 2 | **NO autorizado.** No entrenar modelos definitivos sin autorización expresa |
| Mercado (congelado) | Fútbol, **Over/Under 2,5 goles, solo prepartido**, tiempo reglamentario |
| Universo | 22 divisiones de Football-Data.co.uk; exclusiones solo por criterios objetivos predefinidos (`configs/exclusion_criteria.json`) |
| Fuente principal | Football-Data.co.uk |
| Prueba final | **2024/25 y 2025/26: SELLADAS** |
| Reserva prospectiva | **2026/27+: SELLADA** (decisión conservadora de GATE 1) |
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
- **Nunca** nombrar rutas reservadas (`data/holdout`, `data/prospective`) fuera de
  `paths.py`/`holdout.py`; el test tripwire lo impide.
- **Nunca crear `HOLDOUT_AUTHORIZATION.json` ni `PROSPECTIVE_AUTHORIZATION.json`** sin una
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
data/holdout/, data/prospective/          SELLADOS (raw, processed, registry, ACCESS_LOG)
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
| 1 Infraestructura de datos | Completado; pendiente de revisión |
| 2 Modelo inicial | No autorizado |
| 3 Validación histórica | No iniciado |
| 4 Auditoría | No iniciado |
| 5 Prospectivo (simulado) | No iniciado |
| 6 Interfaz | No iniciado |

Si una etapa fracasa: detener, documentar e investigar, y decidir con el usuario.

## 10. Documentos

Fase Cero: `RESEARCH_FOUNDATIONS.md`, `DATA_FEASIBILITY_REPORT.md`,
`MARKET_SELECTION_REPORT.md`. GATE 1: `DATA_INVENTORY.md`, `DATA_QUALITY_REPORT.md`,
`TEMPORAL_INTEGRITY_REPORT.md`, `HOLDOUT_PROTECTION_PROTOCOL.md`,
`MARKET_BENCHMARK_SPECIFICATION.md`, `EXPERIMENTAL_PROTOCOL.md`, `MODEL_ROADMAP.md`,
`GATE_1_REPORT.md`. Transversales: `LIMITATIONS.md`, `EXPERIMENT_LOG.md`, `ROADMAP.md`,
`README.md`. Futuros: `MODEL_SPECIFICATION.md` (G2), `BACKTEST_REPORT.md` (G3),
`MODEL_AUDIT_REPORT.md` (G4).

## 11. Decisiones pendientes del usuario

1. Revisar y aprobar GATE 1; autorizar o no GATE 2.
2. Confirmar el sellado conservador de 2026/27.
3. Revisar los 4 alias de equipos basados en juicio (`configs/team_aliases.json`).
4. Repositorio remoto (GitHub) opcional para persistencia adicional.

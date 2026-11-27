# CLAUDE.md — Quantitative Sports Intelligence

Instrucciones permanentes del proyecto. Todo agente (humano o IA) que trabaje en este
repositorio debe leer este archivo antes de actuar. Ante conflicto, prevalece la
instrucción explícita más reciente del usuario.

## 1. Misión

Construir conocimiento predictivo **verificable** sobre un único mercado deportivo.

- **H1 (predictiva):** ¿un modelo cuantitativo especializado produce probabilidades que
  mejoran consistentemente, fuera de muestra, las probabilidades implícitas del mercado?
- **H2 (económica):** ¿esa mejora se traduce en valor esperado positivo con precios
  efectivamente disponibles, incertidumbre estadística y condiciones de ejecución reales?

Ninguna hipótesis se presupone verdadera. Un resultado negativo válido es preferible a
un resultado positivo defectuoso. Este proyecto **no** es un servicio de pronósticos ni
de recomendaciones de apuestas.

## 2. Estado actual y alcance autorizado

| Elemento | Estado |
|---|---|
| Fase | **Fase Cero completada — GATE 0 pendiente de aprobación del usuario** |
| Mercado recomendado | Fútbol, Over/Under 2,5 goles a tiempo reglamentario (ver `MARKET_SELECTION_REPORT.md`) |
| Mercado aprobado | **Ninguno todavía** |
| Motor predictivo | **No autorizado** hasta aprobación de GATE 0 |
| Conjunto de prueba final | Propuesto: temporadas >= 2024/25 **selladas** (ver §6) |

Mientras GATE 0 no esté aprobado: no entrenar modelos, no construir features, no
ejecutar backtests económicos. Una vez aprobado un mercado, **el alcance queda
congelado**: no añadir mercados, deportes, líneas (p. ej. 1,5/3,5) ni competiciones
fuera del universo preregistrado sin autorización expresa del usuario.

## 3. Principios no negociables

1. Nunca inventar datos, estadísticas, cuotas, resultados ni referencias.
2. Ninguna probabilidad proviene de la intuición de un modelo de lenguaje: toda
   probabilidad debe poder reproducirse ejecutando código con los mismos datos y parámetros.
3. Una estimación no es la probabilidad verdadera. Ningún resultado es "seguro".
4. Nunca usar información futura (point-in-time estricto).
5. Nunca optimizar nada con el conjunto de prueba final; una vez examinado, deja de ser
   independiente.
6. Registrar todos los experimentos, incluidos los negativos (`EXPERIMENT_LOG.md`).
7. No seleccionar retrospectivamente experimentos, ligas, umbrales o ventanas exitosas.
8. Una racha, un alto % de aciertos o un ROI retrospectivo aislado no demuestran nada.
9. Nunca usar cuotas ficticias (p. ej. suponer -110 o "cuota justa" del modelo) para
   evaluar rentabilidad.
10. **Nunca** desarrollar automatización de apuestas con dinero real.
11. No eludir bloqueos de acceso, CAPTCHAs ni términos de uso (ver §8).
12. Cuando falte evidencia, decirlo con estas etiquetas: `EVIDENCIA INSUFICIENTE`,
    `MODELO NO VALIDADO`, `DATOS NO DISPONIBLES`, `VENTAJA ESTADÍSTICA NO DEMOSTRADA`.

## 4. Fundamentos matemáticos (convenciones obligatorias)

- Probabilidad implícita: `p_imp = 1/Q` (umbral de equilibrio, no probabilidad verdadera).
- Overround de un mercado **completo**: `sum(1/Q_i) - 1` (1X2 = tres resultados; O/U = dos).
- Eliminación del margen (inicial): normalización proporcional `p_i = (1/Q_i)/sum(1/Q_j)`.
  Métodos alternativos (power, Shin) solo con justificación empírica y documentación de
  supuestos. Nota verificada: para dos resultados, Shin y el método aditivo coinciden
  (Clarke et al. 2017).
- Valor esperado binario sin devolución: `EV = p·Q - 1`. No descontar de nuevo el margen.
  Casos de prueba obligatorios: (0,62; 1,80)→+11,6%; (0,60; 1,80)→+8,0%;
  (0,55; 1,80)→-1,0%; (0,60; 3,00)→+80,0%.
- Poisson independiente: `P(Over 2,5) = 1 - e^{-λ}(1 + λ + λ²/2)`, `λ = λ_home + λ_away`.
- Advertencia Dixon-Coles: su corrección actúa sobre 0-0, 1-0, 0-1 y 1-1, todos Under 2,5;
  con intensidades fijas se compensa en el agregado O/U 2,5. Cualquier mejora debe
  provenir de la estimación de parámetros y verificarse empíricamente.
- Distinguir siempre: xG histórico observado ≠ intensidad futura estimada ≠ goles reales.
- Incertidumbre: separar aleatoria, de parámetros, de modelo y de datos. No llamar
  "intervalo de confianza/credibilidad" a un rango que no lo sea.

## 5. Arquitectura de datos

```
data/raw/        originales inmutables + manifest.jsonl (URL, fecha UTC, SHA-256)
data/processed/  normalizados y validados (GATE 1)
data/features/   variables point-in-time (GATE 2+)
```

- RAW nunca se sobrescribe ni se edita. Los archivos RAW no se versionan en git
  (se re-descargan y se verifican por SHA-256).
- Cada registro procesado debe conservar: id de evento, competición, temporada,
  fecha/hora, participantes, fuente, **momento de disponibilidad**, fecha de recolección,
  versión del dataset, indicadores de calidad y faltantes.
- Distinguir fecha del evento de fecha de disponibilidad del dato.
- Imputación solo con información dentro de la ventana de entrenamiento y documentada.
- Particularidades conocidas de Football-Data (ver `DATA_FEASIBILITY_REPORT.md`):
  filas con más campos que la cabecera (2001-2008), alias `HT/AT` en archivos griegos
  antiguos, cuotas pre-cierre capturadas viernes/martes por la tarde, cuotas de
  Pinnacle **no fiables desde el 23/07/2025**.

## 6. Validación

- División cronológica: entrenamiento → validación/selección → prueba final.
- Walk-forward con ventanas expansivas/móviles; evaluación por temporada y por liga.
- **Prohibida** la división aleatoria como validación principal.
- **Sellado propuesto:** los RESULTADOS de las temporadas >= 2024/25 no se examinan
  hasta que hipótesis, métricas, modelos y umbrales estén congelados y registrados.
  En Fase Cero solo se usaron para cobertura y márgenes (que no dependen de resultados).
  Pendiente de confirmación del usuario.
- Pruebas de leakage obligatorias: información futura, estadísticas del propio partido,
  cuotas posteriores al momento de predicción, transformaciones ajustadas con prueba,
  duplicados, contaminación entre conjuntos.
- Selección múltiple: registrar todo; preregistrar hipótesis y métricas antes de abrir
  la prueba final; controlar falsos descubrimientos (p. ej. Benjamini-Hochberg, White
  Reality Check / Hansen SPA cuando se comparen muchas variantes).

## 7. Evaluación

- Predictiva (primaria): log loss, Brier, comparación pareada contra el mercado sin
  margen (Diebold-Mariano o bootstrap por bloques), calibración (diagrama de fiabilidad,
  pendiente e intercepto, ECE), discriminación y nitidez **por separado**.
- Económica (secundaria y separada): solo con cuotas históricas reales del momento de
  predicción; ROI, drawdown, rachas, CLV (`Q_obtenida/Q_cierre - 1`) como indicador
  complementario. Si no hay cuotas de Coolbet, rotular explícitamente el operador usado.
- Referencia medida en Fase Cero (temporadas 2019/20-2023/24, 22 divisiones): Brier del
  mercado de cierre O/U 2,5 sin margen ≈ 0,2406 frente a ≈ 0,25 de la climatología
  (dentro de muestra). Cualquier modelo debe batir al mercado, no a la climatología.

## 8. Fuentes y restricciones legales

- Football-Data.co.uk: gratuita; fuente principal candidata.
- Sports Reference (Basketball-Reference, FBref): sus términos prohíben usar sus datos
  para "machine learning methods used to predict" y limitan a 10-20 peticiones/min.
  **No usar para modelos.**
- stats.nba.com / Understat / FBref: no accesibles desde el entorno cloud (bloqueo o
  desafío anti-bot). **No eludir.**
- The Odds API: históricos de pago (desde jun-2020; incluye Coolbet). Requiere
  aprobación del usuario antes de cualquier gasto.

## 9. Convenciones de código

- Python >= 3.11 (entorno actual: 3.13). Dependencias mínimas: NumPy, SciPy, pandas,
  statsmodels, scikit-learn, DuckDB/Parquet, Matplotlib, pytest. Añadir otras solo con
  justificación escrita.
- Funciones puras para la matemática de cuotas; tipado; docstrings con la fórmula.
- Semillas fijas en todo proceso aleatorio; configuración en `configs/`.
- Cada script de experimento escribe sus salidas en `reports/` o `experiments/` con la
  versión del dataset (hash) y los parámetros.
- Tests con pytest; casos matemáticos verificables independientemente
  (p. ej. Poisson λ=1: P(X=0) ≈ 0,367879) y tolerancia documentada para truncamiento.
- No crear módulos vacíos para aparentar arquitectura.
- Sin frontend, microservicios, nube compleja ni autenticación hasta GATE 6.

## 10. Puertas de validación

| Gate | Requisito resumido | Estado |
|---|---|---|
| 0 | Investigación, fuentes auditadas, cuotas verificadas, mercado seleccionado, aprobación | **Pendiente de aprobación** |
| 1 | Dataset real, integridad, timestamps, ingesta reproducible, tests | No iniciado |
| 2 | Modelo interpretable, baselines, probabilidades reproducibles | No iniciado |
| 3 | Backtest cronológico vs mercado, calibración, incertidumbre, negativos incluidos | No iniciado |
| 4 | Auditoría adversarial, estabilidad, leakage, sobreajuste, sensibilidad | No iniciado |
| 5 | Validación prospectiva preregistrada, solo simulada | No iniciado |
| 6 | Interfaz (solo si 0-5 aportan evidencia sólida) | No iniciado |

Si una etapa fracasa: no avanzar; documentar, investigar causas y decidir con el
usuario si corregir o abandonar la hipótesis.

## 11. Documentos del proyecto

Existentes: `README.md`, `RESEARCH_FOUNDATIONS.md`, `DATA_FEASIBILITY_REPORT.md`,
`MARKET_SELECTION_REPORT.md`, `EXPERIMENT_LOG.md`, `LIMITATIONS.md`, `ROADMAP.md`.
Se crearán al llegar a su gate (no antes, para no generar documentos vacíos):
`MODEL_SPECIFICATION.md` (G2), `BACKTEST_REPORT.md` (G3), `MODEL_AUDIT_REPORT.md` (G4).

## 12. Decisiones pendientes (requieren al usuario)

1. Aprobar o rechazar el mercado recomendado (GATE 0).
2. Confirmar el sellado de temporadas >= 2024/25 como prueba final.
3. Universo de competiciones: propuesta = las 22 divisiones de Football-Data, sin
   selección retrospectiva de ligas.
4. Gasto opcional en The Odds API (cuotas históricas de Coolbet desde 2020).
5. Repositorio remoto (GitHub) para persistir el trabajo: el contenedor actual es efímero.

# ROADMAP

Avance por puertas. Ninguna etapa empieza sin cerrar la anterior y, en GATE 0, sin
aprobación del usuario. Las fechas no se fijan: dependen de los resultados.

## GATE 0 — Selección del mercado · *pendiente de aprobación*
- [x] CLAUDE.md con reglas permanentes
- [x] Investigación bibliográfica verificada (`RESEARCH_FOUNDATIONS.md`)
- [x] Auditoría de fuentes (`DATA_FEASIBILITY_REPORT.md`)
- [x] Matriz y sensibilidad (`MARKET_SELECTION_REPORT.md`)
- [ ] **Aprobación del usuario del mercado, el sellado y el universo**

## GATE 1 — Infraestructura de datos (si se aprueba O/U 2,5)
1. Módulo `src/markets/odds.py`: probabilidad implícita, overround de mercado completo,
   normalización proporcional y de potencia, EV. Tests con los 4 casos de referencia del
   encargo.
2. Ingesta `src/ingestion/football_data.py`: parser tolerante (columnas extra, alias,
   cabeceras duplicadas), esquema normalizado y Parquet en `data/processed/`.
3. Point-in-time: columna `odds_available_at` reconstruida (regla viernes/martes),
   `kickoff_at`, `result_available_at`.
4. Validación (`src/validation/`): cuotas ≥ 1,01, overround en rango, duplicados,
   coherencia de resultados, liquidación O/U (`FTHG+FTAG > 2,5`).
5. Pruebas de leakage desde el inicio: ninguna feature con timestamp ≥ momento de
   predicción.
6. Añadir dependencias justificadas: SciPy, statsmodels, DuckDB, PyArrow.

## GATE 2 — Modelo inicial
1. Baselines: tasa histórica por liga (expanding), promedio de la competición, mercado
   sin margen (proporcional y potencia).
2. Modelo principal: Poisson independiente ataque/defensa/localía por liga, con
   ponderación temporal y regularización, más la fórmula analítica de P(Over 2,5).
3. `MODEL_SPECIFICATION.md` con supuestos, prioridades y preregistro de hipótesis:
   - H1a: Poisson con ponderación temporal frente al mercado.
   - H1b: inclusión de tiros y tiros a puerta (Wheatcroft) frente a solo goles.
   - H1c: modelo asistido por mercado `logit(p) = logit(p_mkt) + f(X)` regularizado.

## GATE 3 — Validación histórica
- Walk-forward por jornada; log loss, Brier, calibración y discriminación; comparación
  pareada contra el mercado con bootstrap por bloques (jornada y liga); Diebold-Mariano;
  control de multiplicidad (BH, SPA).
- Evaluación económica separada con Bet365, promedio y máximo; CLV.
- `BACKTEST_REPORT.md`, con resultados negativos incluidos.
- Apertura **única** del conjunto sellado al final.

## GATE 4 — Auditoría adversarial
- `MODEL_AUDIT_REPORT.md`: estabilidad por temporada y liga, dependencia de variables,
  sensibilidad al momento de captura, PBO.

## GATE 5 — Laboratorio prospectivo (solo simulado)
- Registro append-only de predicciones antes de cada partido. Métricas principales: log
  loss frente al mercado, calibración y CLV. El ROI es secundario por potencia (ver
  `MARKET_SELECTION_REPORT.md` §6).
- Paper betting con saldo hipotético de 9.000 CLP, unidad de 1.000 CLP (y unidades
  menores), tope de cuota 3,50, incluidos los escenarios de ruina.

## GATE 6 — Interfaz
Solo si las etapas 0-5 aportan evidencia sólida.

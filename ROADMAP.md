# ROADMAP

Avance por puertas. Ninguna etapa empieza sin cerrar la anterior y, en GATE 0, sin
aprobación del usuario. Las fechas no se fijan: dependen de los resultados.

## GATE 0 — Selección del mercado · **APROBADO (2026-11-27)**
- [x] CLAUDE.md con reglas permanentes
- [x] Investigación bibliográfica verificada (`RESEARCH_FOUNDATIONS.md`)
- [x] Auditoría de fuentes (`DATA_FEASIBILITY_REPORT.md`)
- [x] Matriz y sensibilidad (`MARKET_SELECTION_REPORT.md`)
- [x] Aprobación del usuario (O/U 2,5 prepartido, 22 divisiones, holdout 2024/25-2025/26)

## GATE 1 — Infraestructura de datos · **COMPLETADO, pendiente de revisión** (ver `GATE_1_REPORT.md`)
Implementado y probado (paquete `src/qsports/`, 59 pruebas):
- [x] `odds.py`, `ou.py`: probabilidad implícita, overround, normalización proporcional y de potencia, EV, CLV, liquidación, Poisson
- [x] `ingest.py`: descarga enrutada por partición; parser tolerante; esquema canónico; procedencia por fila
- [x] `temporal.py`: regla de captura, corte de información conservador, ambigüedad, hora UK → UTC
- [x] `holdout.py`: separación física, registro de ids, guardas, autorización ligada al protocolo, log de accesos
- [x] `benchmark.py`: A/A′/A*/B/C, reglas por fuente/período (Pinnacle), muestras idénticas
- [x] `quality.py`, `verify.py`: inventario (nivel 0), calidad, exclusiones, diagnósticos, hashes
- [x] Reconstrucción desde cero verificada; `requirements-lock.txt`
- Dependencias de GATE 2 (SciPy y, si se justifica, statsmodels) se añadirán al iniciar GATE 2

## GATE 2 — Modelo inicial · **NO AUTORIZADO** (detalle en `MODEL_ROADMAP.md`)
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

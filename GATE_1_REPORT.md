# GATE_1_REPORT — Informe ejecutivo de GATE 1 (Infraestructura de datos)

Fecha: 2026-11-27 · Estado: **COMPLETADO, pendiente de revisión del usuario** ·
GATE 2: **no iniciado ni autorizado** · Holdout: **sellado, 0 accesos**

## 1. Resumen

La infraestructura de datos para investigar el mercado Over/Under 2,5 en las 22
divisiones de Football-Data está implementada, probada y es reproducible desde cero:
- El conjunto de prueba final (2024/25-2025/26) está físicamente separado y protegido por
  controles automáticos.
- Los benchmarks de mercado y elementales están especificados e implementados con reglas
  explícitas por fuente y período.
- El protocolo experimental está diseñado sin haber entrenado ningún modelo.

**No se encontró ningún problema crítico de datos ni de metodología que impida avanzar.**
Hay limitaciones importantes, y la principal es la ausencia de cuotas históricas de
Coolbet (§7).

## 2. Trabajo completado

| Requisito de la autorización | Estado | Dónde |
|---|---|---|
| 2. Protección del holdout (separación física, controles automáticos, manifiesto de hashes, registro de exposición) | Hecho | `HOLDOUT_PROTECTION_PROTOCOL.md`, `src/qsports/holdout.py` |
| 3. Inventario de las 22 divisiones | Hecho (589 división-temporadas) | `DATA_INVENTORY.md`, `reports/gate1/inventory_*.csv` |
| 3. Exclusiones solo por criterios objetivos predefinidos | Hecho: ninguna división excluida | `configs/exclusion_criteria.json`, `DATA_QUALITY_REPORT.md` §4 |
| 4. Arquitectura point-in-time | Hecho | `TEMPORAL_INTEGRITY_REPORT.md`, `src/qsports/temporal.py` |
| 5. Benchmark de mercado (proporcional, por casa, consenso, muestras idénticas, A/B/C) | Hecho | `MARKET_BENCHMARK_SPECIFICATION.md`, `src/qsports/benchmark.py` |
| 6. Tratamiento de Pinnacle | Hecho | Regla `PIN-2025-07-23`, `reports/gate1/pinnacle_investigation.json` |
| 7. Separación de Q1, Q2 y Q3 | Hecho | `EXPERIMENTAL_PROTOCOL.md` §1 |
| 8. Protocolo M0-M5 (sin entrenar) | Hecho | `MODEL_ROADMAP.md` |
| 9. Heterogeneidad entre competiciones | Diseñado | `MODEL_ROADMAP.md` |
| 10. Métricas, incertidumbre, potencia y criterios preregistrados | Diseñado (umbrales a confirmar al congelar) | `EXPERIMENTAL_PROTOCOL.md` §3-6 |
| 11. Persistencia y reproducibilidad | Hecho y verificado | `README.md`, `requirements-lock.txt`, archivo descargable |
| 12. Entregables (9 documentos) | Hecho | Raíz del repositorio |

## 3. Resultados verificables

| Resultado | Valor | Cómo verificarlo |
|---|---|---|
| Filas de desarrollo (2000/01-2023/24) | 182.821 | `MANIFEST.json`; `python -m qsports verify` |
| Universo de entrenamiento | 182.818 | `reports/gate1/exclusions.json` |
| Muestra primaria de comparación con el mercado (A, 2005/06-2023/24) | 146.350 | ídem |
| Muestra con cierre (A + B, 2019/20-2023/24) | 37.953 | `benchmark_coverage.json` |
| Holdout (filas, nivel 0) | 15.328 | `data/holdout/registry.json` |
| Reserva prospectiva (filas, nivel 0) | 2.680 | `data/prospective/registry.json` |
| Divisiones excluidas | 0 de 22 | `exclusions.json` |
| Filas perdidas por el parser | 0 (8.038 filas anchas recuperadas) | `DATA_QUALITY_REPORT.md` |
| Versión del dataset | `fd-2026-11-27-41d9503c0d33` | `MANIFEST.json` |
| Reconstrucción desde cero (clon limpio + venv + descarga nueva) | Hashes RAW y de contenido **idénticos** en los 7 artefactos | §5 |

## 4. Problemas encontrados y cómo se resolvieron

| Problema | Gravedad | Resolución |
|---|---|---|
| El primer intento de separación física (`git mv -k`) no movió los archivos | Alta, potencial | Detectado al listar el directorio; corregido con `mv` antes de cualquier otro paso; hashes verificados |
| Variante de nombre "Raith"/"Raith Rvs" (mismo club, misma temporada), no detectada por la primera prueba | Media (identidad de equipos para M1/M2) | Búsqueda sistemática de variantes; 25 candidatos revisados; 5 alias aplicados (1 empírico, 4 por juicio) |
| Fila artefacto `#REF!` (Excel) en T1 2013/14 | Baja | Excluida por criterio objetivo (sin fecha) |
| 2 partidos griegos sin resultado | Baja | Excluidos del entrenamiento |
| 16 filas con tiros a puerta > tiros; 1 partido con 9 rojas; 1 HTR incoherente | Baja (afecta a M3) | Banderas por fila; ningún valor modificado |
| Hash de contenido distinto entre reconstrucciones | Media (reproducibilidad) | Causa verificada: solo la marca de descarga. Se excluye del hash y se registra aparte |
| Un módulo nombraba rutas reservadas (solo para leer fechas de descarga) | Baja | Movido a `holdout.py`; el tripwire lo impide en adelante |
| Invariante temporal en falso por 1 fila sin fecha | Ninguna (falso positivo) | Comprobación corregida |

## 5. Pruebas ejecutadas (resultados reales)

- **pytest: 59 de 59 aprobadas** (salida completa en `reports/gate1/pytest_result.txt`):
  - Matemática (14): los 4 casos de EV del encargo, probabilidades implícitas, overround,
    proporcional, potencia, CLV, liquidación y Poisson (λ = 1: P(0) = 0,367879; masa
    truncada < 1e-12).
  - Parser (5): filas anchas, alias, cabeceras duplicadas, codificaciones, `#REF!`, alias
    de equipos, banderas.
  - Temporal (10): regla por día de la semana, corte estricto, ambigüedad, cambio de
    horario BST/GMT.
  - Benchmarks (5): validez, Pinnacle sin eliminar partidos, máximos excluidos, muestras
    comunes, frecuencia point-in-time.
  - Protección del holdout (14): particiones, guardas, ids re-etiquetados, autorización
    ligada al hash del protocolo, log de accesos, tripwire, nivel 0 sin valores.
  - Integración (11): datos reales, leakage del benchmark C por fuerza bruta,
    `verify_all`.
- **`python -m qsports verify`: 10 de 10 comprobaciones ok**; holdout y prospectivo
  sellados; 0 accesos registrados.
- **Pruebas de mutación:** un script que lee `data/holdout` hizo fallar el tripwire; un
  byte alterado en un `data.zip` sellado fue detectado por `verify`.
- **Reconstrucción desde cero:** clon git limpio, venv nuevo con
  `requirements-lock.txt`, 27 temporadas descargadas de nuevo (hashes iguales a la
  descarga original), construcción completa: contenido idéntico en desarrollo, nivel 0,
  benchmarks y particiones selladas (comparación de hashes, sin abrir datos reservados).
  Las 59 pruebas también pasan en el clon.

## 6. Decisiones metodológicas tomadas

1. **2026/27 sellada** como reserva prospectiva (conservador: es posterior al holdout).
   **Requiere tu confirmación.**
2. **Benchmark principal A** = promedio pre-cierre de la fuente, normalizado de forma
   proporcional. Es el único con cobertura pre-cierre en todo el desarrollo. Se reporta por
   régimen (Betbrain/Oddsportal).
3. **Corte de información:** solo resultados con fecha estrictamente anterior a la captura
   estimada (viernes o martes). Nunca resultados del mismo día. El modelo nunca tiene más
   información que la cuota de referencia.
4. **Partidos ambiguos** (inicio antes del límite de captura) excluidos de la muestra
   primaria de comparación (235).
5. **Pinnacle:** todas sus cuotas se enmascaran desde el 23/07/2025, sin eliminar
   partidos. No es necesario en desarrollo; no está disponible en el holdout desde
   feb-2026.
6. **Prohibido combinar casas** para probabilidades o márgenes. El par de máximos tiene
   margen negativo en el 5-26% de los partidos.
7. **Identidad de equipos:** 5 alias (4 por juicio, **para tu revisión**). `match_id`
   estable con nombres crudos.
8. **Exposición de la Fase Cero:** registrada. Ningún resultado reservado observado. La
   elección O/U frente a 1X2 se reproduce idéntica solo con desarrollo. Riesgo residual
   bajo.

## 7. Limitaciones pendientes (detalle en `LIMITATIONS.md`)

1. **Fundamental:** sin cuotas históricas de Coolbet. Q3 se evaluará con Bet365 y
   agregados, sin extrapolar a Coolbet.
2. Momento de captura pre-cierre estimado por regla (sin timestamp por fila). 22.946
   partidos de viernes/martes antes de 2019/20 no son verificables.
3. Cambio de régimen de los promedios en 2019/20. El holdout es homogéneo (Oddsportal).
4. Sin xG histórico. Estadísticas completas en las 22 divisiones solo desde 2017/18.
5. Identidad de equipos por nombre (clubes refundados).
6. Potencia: MDE preliminar ≈ 0,0029 nats en el holdout con una variabilidad sustituta
   (σ_Δ = 0,114). Mejoras pequeñas podrían no ser detectables. Q3 probablemente será
   inconclusa por potencia.
7. La protección del holdout cubre el uso accidental; el uso deliberado se cubre por
   procedimiento.

## 8. Recomendaciones para GATE 2 (si lo autorizas)

1. Empezar por **M0** (ya implementado como benchmarks) y **M1 Poisson** con
   identificabilidad por suma cero y regularización L2, en walk-forward sobre el desarrollo
   interno (2005/06-2021/22). Añadir SciPy como dependencia.
2. Implementar en paralelo el **evaluador** (Δ log loss pareada, bootstrap por bloques de
   semanas, Diebold-Mariano, calibración) y probarlo con benchmarks conocidos antes de
   evaluar modelos.
3. Medir σ_Δ real de M1/M2 frente a A para recalcular la potencia y fijar el SESOI antes
   de comparar candidatos en la validación de desarrollo.
4. Priorizar **M4-cal frente a M4-sport**: es la forma más directa de separar "mejorar el
   mercado por calibración" de "aportar información deportiva".
5. Mantener el número de familias candidatas pequeño (≤ 3 en la validación) para limitar
   la selección múltiple.

## 9. Decisiones que necesito de ti

1. ¿Apruebas GATE 1?
2. ¿Confirmas el **sellado de 2026/27** como reserva prospectiva?
3. ¿Aceptas los **4 alias de equipos por juicio** (OFI → OFI Crete, Roda → Roda JC,
   Sparta → Sparta Rotterdam, Boston → Boston Utd)?
4. ¿Autorizas el inicio de **GATE 2** con el alcance del §8?

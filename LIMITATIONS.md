# LIMITATIONS — Limitaciones conocidas

Documento vivo · Última actualización: 2026-11-27 (GATE 1)

## Limitación fundamental
| # | Limitación | Consecuencia |
|---|---|---|
| **F1** | **No existen cuotas históricas de Coolbet** en ninguna fuente gratuita (la única opción, The Odds API de pago, está excluida por decisión del usuario) | Q3 solo puede evaluarse con Bet365 y agregados de mercado. **Ningún resultado económico se extrapola a Coolbet.** El margen de Coolbet es desconocido |

## Datos
| # | Limitación | Impacto | Mitigación |
|---|---|---|---|
| D1 | Sin timestamp por fila de la captura pre-cierre; la regla viernes/martes es una política publicada hoy y se **supone** para el pasado | Point-in-time aproximado | Corte conservador (resultados estrictamente anteriores a la fecha de captura); verificación indirecta por gradiente de movimiento (TEMPORAL_INTEGRITY_REPORT §5); sensibilidad −1 día |
| D2 | Sin hora de inicio antes de 2019/20: 22.946 partidos de viernes/martes con captura no verificable | Posible desajuste informativo en esos partidos | Sensibilidad preregistrada que los excluye |
| D3 | Pinnacle no fiable desde el 23/07/2025 y ausente desde feb-2026 | Sin referencia "sharp" en el holdout | Regla PIN-2025-07-23; benchmarks A, A′-Bet365, B disponibles |
| D4 | Cambio de régimen Betbrain → Oddsportal (2019/20); Pinnacle sale de los promedios (07/2025) | Benchmark A no homogéneo en el tiempo | Reporte por régimen; el holdout es homogéneo (Oddsportal) |
| D5 | Sin xG histórico gratuito, legal y accesible | Predictores limitados a goles, tiros, tiros a puerta y córners | xG solo prospectivo (2026/27+) |
| D6 | Estadísticas completas en las 22 divisiones solo desde 2017/18 | M3 con faltantes estructurales antes de 2017/18 | Indicadores de faltante + análisis restringido preregistrado |
| D7 | Identidad de equipos por nombre; clubes refundados con el mismo nombre quedan fusionados (p. ej. Chester) | Ruido en fuerzas de equipos de divisiones inferiores | 5 alias documentados; el resto queda como limitación |
| D8 | Errores puntuales en estadísticas (16 tiros a puerta > tiros, 1 partido con 9 rojas) | Ruido en M3 | Banderas por fila; exclusión en medias móviles |
| D9 | Sin licencia formal de Football-Data | Incertidumbre sobre redistribución | No se redistribuyen CSV; reconstrucción por descarga + SHA-256 |
| D10 | Partidos aplazados: no se sabe para qué fecha se capturó la cuota pre-cierre | Posible desajuste puntual | Ninguna disponible; impacto previsto bajo |
| D11 | No se sabe si la fuente corrigió datos históricos tras publicarlos | Versiones de datos no observables hacia atrás | Hashes detectan cambios desde hoy |
| D12 | Validez de valores (goles, cuotas) en el holdout **no evaluada** (sellado) | Posibles errores por descubrir al abrir | Mismas comprobaciones automáticas tras la autorización |

## Protección del holdout
| # | Limitación |
|---|---|
| H1 | Los controles impiden el uso **accidental**, no el deliberado por alguien con acceso al disco; la protección deliberada es de procedimiento (CLAUDE.md + registro de accesos) |
| H2 | Exposición previa de nivel 1 (agregados de cuotas) en la Fase Cero, sin resultados; evaluada como de riesgo bajo (HOLDOUT_PROTECTION_PROTOCOL §5) |
| H3 | 2026/27 sellada por decisión conservadora; reduce los datos disponibles para desarrollo |

## Evidencia científica
| # | Limitación |
|---|---|
| L1 | Solo un estudio leído en texto completo (Wheatcroft 2020) |
| L2 | Una sola línea de investigación sobre ineficiencia en O/U 2,5; su rentabilidad exige cuotas máximas |
| L3 | Sesgo de publicación probable |

## Estadística
| # | Limitación |
|---|---|
| S1 | MDE preliminar en el holdout ≈ 0,0029 nats (σ_Δ sustituto 0,114; deff 1,23); mejoras menores pueden no ser detectables |
| S2 | ROI: detectar 2% requiere ~14.700 apuestas independientes; Q3 probablemente inconclusa |
| S3 | El mercado mejora a la frecuencia histórica solo en 0,0083 nats (desarrollo interno); el margen absoluto de mejora es pequeño |

## Ejecución
| # | Limitación |
|---|---|
| X1 | Limitación de cuentas ganadoras (Kaunitz et al. 2017, preprint), no capturada por backtests |
| X2 | Precios del dataset ≠ precios disponibles para el usuario (casa, momento, límites) |

## Entorno
| # | Limitación | Mitigación |
|---|---|---|
| E1 | Contenedor cloud efímero sin repositorio remoto | Archivo descargable con historial git; reconstrucción desde cero verificada |
| E2 | Algunas fuentes bloquean IPs cloud | No se eludió ningún bloqueo |

## GATE 2 (modelos)
| # | Limitación | Impacto |
|---|---|---|
| G1 | Conjunto de información limitado (goles, tiros, tiros a puerta, córners, cuotas pre-cierre); sin xG histórico, alineaciones, lesiones, clima | El "aporte deportivo no demostrado" se refiere a este conjunto |
| G2 | M1 quedó en el borde de la grilla de ridge tras 3 extensiones (D-1) | M1 puede estar algo subregularizado; no afecta a M2 ni a M4 |
| G3 | Grillas modestas y búsqueda por grilla, no optimización continua | Óptimos aproximados; diferencias entre vecinos < 4·10⁻⁴ (Poisson) y < 10⁻⁵ (M3) |
| G4 | Criterio de parada de Newton sensible a la precisión numérica (226 falsos "sin convergencia") | GATE 2.1: verificados los 226 uno a uno; todos alcanzan un criterio 100× más estricto, \|Δp\| ≤ 2,7·10⁻⁸, impacto en log loss media ≤ 4,5·10⁻¹² (`GATE_2_1_REPORT.md` §4). Mejora del criterio pendiente |
| G5 | La prueba interna es de desarrollo; las categorías no son veredictos | Confirmación formal solo en GATE 3 y en el holdout |
| G6 | Primeras temporadas de M3 y M4 con poco entrenamiento (NaN excluidos) | Muestras comunes algo menores al inicio del bloque de ajuste |

## GATE 2.1 (correcciones de auditoría)
| # | Limitación | Impacto |
|---|---|---|
| G7 | Con dependencia serial muy persistente (AR(1) semanal φ = 0,7, sintético), ningún bloque de 2-12 semanas alcanza la cobertura nominal del 95% (82% con 4 semanas, 87% con 12) | Los IC con bloque de 4 semanas podrían ser algo estrechos si la dependencia real fuese así; se informa la autocorrelación semanal real y la sensibilidad a 2-12 semanas (`GATE_2_1_REPORT.md` §3) |
| G8 | La valla de GATE 3 protege las vías del código (motor walk-forward y universo de evaluación). Las temporadas 2022/23-2023/24 pertenecen a la partición de desarrollo y no están selladas físicamente | Una lectura deliberada fuera del código no quedaría registrada; la protección frente a eso es de procedimiento (CLAUDE.md) |
| G9 | D-3: M3 usó el conteo lineal de partidos previos, no log(1 + n) como especificaba el preregistro | Los resultados de M3 de GATE 2 corresponden a la forma lineal; sensibilidad con log1p solo en el bloque de ajuste |
| G10 | La potencia de superioridad y de equivalencia usa una aproximación normal y escala el error estándar de desarrollo por √(n_dev/n_holdout) | Supone estacionariedad de la varianza de Δ y de la dependencia entre desarrollo y holdout |
| G11 | "0 accesos registrados" demuestra que no se usó la apertura autorizada, no la ausencia absoluta de exposición | Exposición previa documentada en HOLDOUT_PROTECTION_PROTOCOL §5 |
| G12 | El prior de ascendidos de M2 (`promoted_prior=True`) promedia sobre un `set` cuyo orden depende de `PYTHONHASHSEED`: no es determinista entre procesos | Diferencias < 10⁻⁸ solo en configuraciones `_pp` (no seleccionadas ni candidatas); corrección de una línea propuesta, pendiente de autorización (`REPRODUCIBILITY_REPORT.md` §3.2) |


## GATE 3 (validación 2022/23-2023/24)
| # | Limitación | Impacto |
|---|---|---|
| V1 | Q3 no evaluada: en el desarrollo no se congeló ninguna regla de selección de apuestas | No hay evidencia de rentabilidad simulada; definir una regla ahora requiere hacerlo antes del holdout y sin optimizarla con la validación |
| V2 | La mejora de M4 sobre A (S-NR) procede de la recalibración de un consenso más comprimido en 2022/23-2023/24 (pendiente 1,20 frente a 1,10 en desarrollo) | Puede no ser estable en el tiempo; no es información deportiva |
| V3 | Un ajuste de M2 en la validación marcado no convergente (F2, 2022-07-29, gradiente 1,0·10⁻⁵) no se pulió, para no volver a tocar la validación | Mismo artefacto que los 226 casos verificados en GATE 2.1 (impacto ≤ 2,7·10⁻⁸ en p) |
| V4 | Validación de dos temporadas (n = 15.488) | IC de M4-sport − M4-cal ±1,2·10⁻⁴; suficiente para EQ frente a δ = 0,001, no para detectar efectos de 10⁻⁴ |

## GATE 4 (congelamiento)
| # | Limitación | Impacto |
|---|---|---|
| F1 | Con la potencia esperada, Q2 solo puede alcanzar S-R si la mejora real de M4-cal sobre A es ≥ ~1,5·10⁻³ (GATE 3 estimó 4,2·10⁻⁴) | El resultado más favorable plausible es S-NR (superioridad estadística sin relevancia demostrada) |
| F2 | La ventaja de M4-cal es una recalibración de la compresión del consenso (b de 1,00 a 1,23 según el período) | Puede variar en el holdout; la condición 2 de Q2 (calibración) lo controla parcialmente |
| F3 | El hash del holdout cargado solo puede verificarse al abrirlo; la equivalencia parquet ↔ hash se apoya en que el desarrollo (mismo procedimiento) la cumple en `verify` | Si no coincidiera, el ejecutor se detiene sin evaluar |
| F4 | M4-cal depende de M2* para definir sus filas de entrenamiento (no para predecir) | Reproducido exactamente: M2* auxiliar en el holdout |
| F5 | Una muerte abrupta del proceso (p. ej. SIGKILL) tras la apertura puede no dejar el estado `interrupted` | El marcador de intento, creado antes de abrir, persiste e impide igualmente el reintento automático |

## Prueba final
| # | Limitación | Impacto |
|---|---|---|
| H1 | El holdout se abrió y se evaluó: ya no puede usarse para evaluar nada posterior | Cualquier nueva hipótesis necesitará datos nuevos (p. ej., validación prospectiva genuina) |
| H2 | Incidente I-1: un segundo acceso al holdout, no evaluativo y posterior al sello | Sin efecto en los resultados (sellados antes), pero el registro muestra 2 accesos |
| H3 | Q2 negativo limitado a la información, los modelos y los períodos evaluados; Q3 no evaluada | No dice nada sobre otras fuentes de información ni sobre rentabilidad |

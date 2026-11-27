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

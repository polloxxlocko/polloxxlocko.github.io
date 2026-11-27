# LIMITATIONS — Limitaciones conocidas

Documento vivo. Cada limitación indica su impacto y cómo se mitiga (si se puede).

## Datos
| # | Limitación | Impacto | Mitigación |
|---|---|---|---|
| D1 | El momento exacto de captura de las cuotas pre-cierre no viene por fila; solo hay una regla publicada (viernes/martes por la tarde) | Reconstrucción point-in-time aproximada | Reconstruir con fecha, día de la semana y hora; análisis de sensibilidad con ventanas alternativas |
| D2 | Pinnacle no fiable desde el 23/07/2025 (fuente + verificación propia) | Sin benchmark "sharp" en la prueba final | Usar promedio y Bet365 de cierre; analizar Pinnacle solo hasta 2024/25 |
| D3 | Cambio de proveedor de promedios/máximos: Betbrain → Oddsportal (2019/20) | Promedios no comparables entre épocas | Analizar por régimen |
| D4 | Sin xG histórico gratuito, legal y accesible | Predictores limitados a goles, tiros y córners | Evaluar xG prospectivamente desde 2026/27 si la fuente lo mantiene |
| D5 | Sin cuotas históricas de Coolbet | H2 no evaluable con el operador real del usuario | Rotular el operador; opción de pago (The Odds API, desde 2020) o registro prospectivo |
| D6 | Sin licencia formal de Football-Data ("My data is free") | Incertidumbre sobre redistribución | Uso privado y de investigación; no redistribuir los CSV |
| D7 | CSV antiguos con formato heterogéneo | Riesgo de errores silenciosos | Parser tolerante + pruebas de integridad en GATE 1 |
| D8 | Árbitro solo en Inglaterra y Escocia | (Relevante solo para tarjetas, fuera de alcance) | — |

## Evidencia científica
| # | Limitación | Impacto |
|---|---|---|
| L1 | Solo un estudio leído en texto completo; el resto a nivel de resumen o metadatos | Detalles metodológicos de otros estudios no verificados |
| L2 | Una sola línea de investigación sobre ineficiencias en O/U 2,5 (Wheatcroft) | Priors débiles sobre H1 y H2 |
| L3 | La rentabilidad publicada depende de cuotas máximas entre muchas casas | No trasladable a un usuario de una sola casa |
| L4 | Sesgo de publicación probable en la literatura de apuestas | Sobreestimación de ventajas en la literatura |

## Estadísticas e inferencia
| # | Limitación | Impacto |
|---|---|---|
| S1 | Detectar ROI pequeños exige miles de apuestas (ROI 2% ≈ 14.700 apuestas independientes) | Validación económica prospectiva inviable a escala individual en plazos cortos |
| S2 | Dependencia entre partidos (misma jornada, mismo equipo) | Los tamaños de muestra "independientes" subestiman lo necesario | 
| S3 | El mercado ya mejora a la climatología solo un ~3,8% en Brier | Diferencias absolutas pequeñas; se necesita mucha muestra para distinguirlas |

## Ejecución
| # | Limitación | Impacto |
|---|---|---|
| X1 | Las casas pueden limitar cuentas ganadoras (Kaunitz et al. 2017, preprint) | Una ventaja demostrada puede no ser explotable |
| X2 | Cuotas disponibles para el usuario ≠ cuotas del dataset (casa, momento, límites) | El backtest sobreestima lo ejecutable |

## Entorno
| # | Limitación | Impacto |
|---|---|---|
| E1 | Contenedor cloud efímero, sin repositorio remoto configurado | El trabajo se pierde si no se sube a GitHub o se descarga |
| E2 | Algunas fuentes bloquean IPs cloud (stats.nba.com, Understat, FBref) | No verificables desde aquí; no se eludió ningún bloqueo |

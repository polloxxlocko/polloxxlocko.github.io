# TEMPORAL_INTEGRITY_REPORT — Arquitectura point-in-time

Versión 1.0 · 2026-11-27 · GATE 1 · Implementación: `src/qsports/temporal.py` ·
Pruebas: `tests/test_temporal.py`, `tests/test_integration.py` · Diagnósticos:
`reports/gate1/temporal_diagnostics.json` (solo desarrollo)

## 1. Campos temporales y su precisión real

| Campo | Significado | Fuente | Precisión |
|---|---|---|---|
| `match_date` | Fecha del partido | `Date` | Día |
| `kickoff_time_uk`, `kickoff_at_utc` | Hora de inicio (hora del Reino Unido → UTC con cambio de horario) | `Time` (desde 2019/20) | Minuto desde 2019/20; antes `kickoff_precision = 'date'` |
| `pre_odds_capture_date_est` | Fecha **estimada** de captura de la cuota pre-cierre | Regla publicada (§2) | `rule_based_date`: **no hay timestamp por fila** |
| `pre_odds_capture_deadline_uk` | Hora límite publicada de esa captura (vie 17:00 / mar 13:00) | `matches.php` | Límite superior, no la hora real |
| `close_odds_capture` | Cuota de cierre ("últimas antes del inicio") | `notes.txt` | Aproximadamente el inicio; sin timestamp |
| `info_cutoff_date` | Solo pueden usarse resultados con fecha **estrictamente anterior** | Regla conservadora (§3) | Día |
| `result_available_date` | Día del partido (resultado conocido al final de ese día) | — | Día |
| `dataset_retrieved_at_utc` | Fecha de descarga del archivo de esa temporada | Manifiesto RAW | Segundo |

**Las cuotas pre-cierre no son cuotas de apertura.** La fuente las captura después de
abrirse el mercado, en la ventana de viernes/martes. En el código se nombran `pre`, nunca
"apertura".

## 2. Regla de captura (verificada en la fuente, aplicada como supuesto histórico)

Texto de `matches.php` (consultado el 2026-11-27): *"odds are collected for the
downloadable weekend fixtures on Fridays afternoons generally not later than 17:00 British
Standard Time. Odds for midweek fixtures are collected Tuesdays not later than 13:00
British Standard Time."*

| Día del partido | Captura asignada | Días entre captura y partido |
|---|---|---:|
| Viernes | Mismo viernes (≤ 17:00) | 0 |
| Sábado | Viernes previo | 1 |
| Domingo | Viernes previo | 2 |
| Lunes | Viernes previo | 3 |
| Martes | Mismo martes (≤ 13:00) | 0 |
| Miércoles | Martes previo | 1 |
| Jueves | Martes previo | 2 |

**Supuesto no verificable por fila:** que esta política (publicada hoy) se aplicó también
en temporadas antiguas (Betbrain, 2005/06-2018/19). `notes.txt` describe la misma regla
sin horas.

## 3. Corte de información conservador

Para predecir un partido solo se usan resultados con `match_date <
pre_odds_capture_date_est`. Consecuencias:
- **Nunca se usan resultados del mismo día.** Su orden relativo no es determinable con la
  precisión disponible, así que se excluyen todos, aunque fueran anteriores.
- El modelo **nunca tiene más información que la cuota pre-cierre** con la que se compara.
  Un sábado se predice con resultados hasta el jueves, aunque los del viernes por la noche
  ya fueran públicos. Este sesgo juega **en contra** del modelo, lo cual es aceptable.
- Invariante verificado en desarrollo: `info_cutoff_date ≤ match_date` en el 100% de las
  filas con fecha. La única fila sin fecha es un artefacto (`#REF!`) excluido.

## 4. Ambigüedad de captura

Si se conoce la hora y el partido empieza **antes** del límite de captura de su día
(viernes < 17:00 o martes < 13:00 UK), la cuota pudo venir de otra captura. Esos partidos
se marcan `capture_rule_ambiguous = True` y se **excluyen de la muestra primaria de
comparación con el mercado**. Siguen en el universo de entrenamiento.

| Diagnóstico (desarrollo) | Valor |
|---|---:|
| Partidos ambiguos 2019/20-2023/24 | 235 (229 viernes, 6 martes) |
| Viernes/martes sin hora (antes de 2019/20): `capture_time_unverifiable` | 22.946 |
| Asignación: fin de semana / mitad de semana | 158.964 / 23.856 |

Los 22.946 partidos sin hora de viernes/martes no se excluyen de la muestra primaria. Se
preregistra un **análisis de sensibilidad** que los excluye (EXPERIMENTAL_PROTOCOL.md).

## 5. Verificación empírica de la regla (desarrollo 2019/20-2023/24, solo cuotas)

Si la regla es correcta, el movimiento entre la cuota pre-cierre y la de cierre debe
**crecer con los días transcurridos desde la captura**:

| Día | Días desde captura | n | Mediana \|Δp\| promedio | Mediana \|Δp\| Bet365 | % Bet365 pre = cierre |
|---|---:|---:|---:|---:|---:|
| Viernes | 0 | 2.908 | **0,0091** | 0,0132 | 27,3% |
| Martes | 0 | 3.638 | **0,0105** | 0,0132 | 24,9% |
| Sábado | 1 | 18.258 | 0,0144 | 0,0186 | 20,4% |
| Miércoles | 1 | 1.969 | 0,0191 | 0,0220 | 19,3% |
| Domingo | 2 | 8.603 | 0,0169 | 0,0202 | 18,5% |
| Jueves | 2 | 650 | 0,0195 | 0,0204 | 15,4% |
| Lunes | 3 | 1.927 | **0,0184** | 0,0202 | 15,7% |

**Lectura:** los días con captura el mismo día (viernes, martes) tienen el menor
movimiento y la mayor proporción de cuotas sin cambio. El movimiento crece de forma
monótona en el ciclo de fin de semana (0 → 1 → 2 → 3 días). Es consistente con la regla e
inconsistente con capturas cercanas al inicio del partido. Los partidos de miércoles y
jueves se mueven algo más que los de sábado y domingo con el mismo desfase, lo que puede
reflejar la llegada de información de alineaciones en rondas de mitad de semana. **Esto
corrobora la regla pero no la prueba por fila.**

## 6. Zona horaria de `Time`

Hora modal de los sábados (2019/20-2023/24): Bundesliga 14:30 (15:30 en Alemania);
2. Bundesliga 12:00 (13:00); Serie A 14:00/19:45 (15:00/20:45); Ligue 1 20:00 (21:00);
La Liga 20:00 (21:00); Primeira Liga 15:30/18:00/20:30 (misma hora en Portugal); ligas
británicas 15:00. **Conclusión: `Time` está en hora del Reino Unido.** Se convierte a UTC
con `Europe/London`. Probado: 15:00 en agosto (BST) → 14:00 UTC; en diciembre → 15:00 UTC.

## 7. Limitaciones temporales

1. Sin timestamp por fila de la captura pre-cierre. La regla es una estimación.
2. Partidos aplazados: la fecha del CSV es la de juego real. Se desconoce si la cuota
   pre-cierre se capturó para la fecha original.
3. Antes de 2019/20 no hay hora de inicio, así que la ambigüedad no es evaluable (22.946
   partidos marcados como no verificables).
4. La cuota de cierre tiene momento aproximado ("antes del inicio"). Por eso solo se usa
   como referencia retrospectiva.
5. Desconocemos si la fuente corrigió datos históricos después de publicarlos. El hash de
   cada descarga permite detectar cambios futuros, no pasados.

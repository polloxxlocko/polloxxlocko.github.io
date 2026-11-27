"""Metadatos de las 22 divisiones de Football-Data.co.uk (universo aprobado en GATE 0).

Nombres de competición según la denominación habitual; Football-Data los identifica
solo por el código `Div`. País según la página de descargas de Football-Data.
"""
from __future__ import annotations

DIVISIONS: dict[str, dict[str, str]] = {
    "E0": {"country": "Inglaterra", "competition": "Premier League", "tier": "1"},
    "E1": {"country": "Inglaterra", "competition": "Championship", "tier": "2"},
    "E2": {"country": "Inglaterra", "competition": "League One", "tier": "3"},
    "E3": {"country": "Inglaterra", "competition": "League Two", "tier": "4"},
    "EC": {"country": "Inglaterra", "competition": "National League (Conference)", "tier": "5"},
    "SC0": {"country": "Escocia", "competition": "Premiership", "tier": "1"},
    "SC1": {"country": "Escocia", "competition": "Championship", "tier": "2"},
    "SC2": {"country": "Escocia", "competition": "League One", "tier": "3"},
    "SC3": {"country": "Escocia", "competition": "League Two", "tier": "4"},
    "D1": {"country": "Alemania", "competition": "Bundesliga", "tier": "1"},
    "D2": {"country": "Alemania", "competition": "2. Bundesliga", "tier": "2"},
    "I1": {"country": "Italia", "competition": "Serie A", "tier": "1"},
    "I2": {"country": "Italia", "competition": "Serie B", "tier": "2"},
    "SP1": {"country": "España", "competition": "La Liga (Primera División)", "tier": "1"},
    "SP2": {"country": "España", "competition": "Segunda División", "tier": "2"},
    "F1": {"country": "Francia", "competition": "Ligue 1", "tier": "1"},
    "F2": {"country": "Francia", "competition": "Ligue 2", "tier": "2"},
    "N1": {"country": "Países Bajos", "competition": "Eredivisie", "tier": "1"},
    "B1": {"country": "Bélgica", "competition": "Pro League (First Division A)", "tier": "1"},
    "P1": {"country": "Portugal", "competition": "Primeira Liga", "tier": "1"},
    "T1": {"country": "Turquía", "competition": "Süper Lig", "tier": "1"},
    "G1": {"country": "Grecia", "competition": "Super League", "tier": "1"},
}

assert len(DIVISIONS) == 22

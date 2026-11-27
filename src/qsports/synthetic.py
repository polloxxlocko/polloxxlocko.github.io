"""Datos sintéticos con verdad conocida (sin datos de la fuente ni datos sellados).

Mundo generativo por división:
  fuerzas att/def de cada equipo: paseo aleatorio por jornada;
  "forma" latente f_i (AR(1)) que afecta a los goles y se refleja en los tiros;
  log λ_home = μ + η + att_h − def_a + f_h,  log λ_away = μ + att_a − def_h + f_a;
  goles ~ Poisson(λ); tiros ~ Poisson(k·exp(log λ + ruido)).
Mercado (cuotas pre-cierre): probabilidad justa = P(Over | λ_mercado) con ruido en logit y margen;
  `market_sees_form=True`: el mercado usa λ verdadero (la forma ya está en el precio);
  `market_sees_form=False`: el mercado ignora la forma (los tiros contienen información
  incremental). Así se puede comprobar que M4-sport supera a M4-cal solo cuando corresponde.
Produce el mismo esquema canónico que `process.build_dev` (subconjunto de columnas usado
por los modelos), incluidos los campos temporales generados con `temporal.add_temporal_fields`.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from . import temporal
from .ou import p_over25_poisson


def _rr_schedule(teams: list[str], rng) -> list[list[tuple[str, str]]]:
    """Doble round robin (método del círculo)."""
    t = teams[:]
    if len(t) % 2:
        t.append(None)
    n = len(t)
    rounds = []
    for r in range(n - 1):
        pairs = [(t[i], t[n - 1 - i]) for i in range(n // 2)]
        pairs = [(a, b) if r % 2 == 0 else (b, a) for a, b in pairs if a and b]
        rounds.append(pairs)
        t = [t[0]] + [t[-1]] + t[1:-1]
    second = [[(b, a) for a, b in rd] for rd in rounds]
    allr = rounds + second
    rng.shuffle(allr)
    return allr


def generate(n_divisions: int = 3, n_teams: int = 16, seasons: tuple[str, ...] = ("0506", "0607", "0708", "0809",
             "0910", "1011", "1112", "1213"), market_sees_form: bool = True, market_noise: float = 0.15,
             form_sd: float = 0.18, form_ar: float = 0.85, strength_drift: float = 0.02, margin: float = 0.06,
             seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(n_divisions):
        div = f"S{d}"
        teams = [f"T{d}_{i:02d}" for i in range(n_teams)]
        att = rng.normal(0, 0.2, n_teams)
        dfn = rng.normal(0, 0.2, n_teams)
        form = np.zeros(n_teams)
        mu, eta = np.log(1.3) + rng.normal(0, 0.05), 0.2 + rng.normal(0, 0.03)
        idx = {t: i for i, t in enumerate(teams)}
        for sc in seasons:
            y0 = 2000 + int(sc[:2])
            start = pd.Timestamp(f"{y0}-08-09")
            start = start + pd.Timedelta(days=(5 - start.weekday()) % 7)  # primer sábado
            for r, rd in enumerate(_rr_schedule(teams, rng)):
                att += rng.normal(0, strength_drift, n_teams)
                dfn += rng.normal(0, strength_drift, n_teams)
                form = form_ar * form + rng.normal(0, form_sd * np.sqrt(1 - form_ar ** 2), n_teams)
                base = start + pd.Timedelta(weeks=r)
                for k, (h, a) in enumerate(rd):
                    i, j = idx[h], idx[a]
                    lh_t = np.exp(mu + eta + att[i] - dfn[j] + form[i])
                    la_t = np.exp(mu + att[j] - dfn[i] + form[j])
                    lh_m = lh_t if market_sees_form else np.exp(mu + eta + att[i] - dfn[j])
                    la_m = la_t if market_sees_form else np.exp(mu + att[j] - dfn[i])
                    p_m = float(p_over25_poisson(lh_m + la_m))
                    z = np.log(p_m / (1 - p_m)) + rng.normal(0, market_noise)
                    p_mk = 1 / (1 + np.exp(-z))
                    o = 1 / (p_mk * (1 + margin)); u = 1 / ((1 - p_mk) * (1 + margin))
                    gh, ga = rng.poisson(lh_t), rng.poisson(la_t)
                    sh = rng.poisson(9 * np.exp(np.log(lh_t) * 0.8 + rng.normal(0, 0.15)))
                    sa = rng.poisson(9 * np.exp(np.log(la_t) * 0.8 + rng.normal(0, 0.15)))
                    dayoff = [0, 0, 0, 1, 1, -1][k % 6]  # sáb/dom/vie
                    date = base + pd.Timedelta(days=dayoff)
                    rows.append({"div": div, "country": f"Synthland{d}", "season_code": sc,
                                 "season": f"{y0}/{(y0 + 1) % 100:02d}", "match_date": date,
                                 "kickoff_time_uk": "15:00" if dayoff >= 0 else "19:45",
                                 "home_team": h, "away_team": a, "fthg": float(gh), "ftag": float(ga),
                                 "hs": float(sh), "as_": float(sa), "hst": float(rng.binomial(sh, 0.35)),
                                 "ast": float(rng.binomial(sa, 0.35)), "hc": float(rng.poisson(5)),
                                 "ac": float(rng.poisson(4.5)),
                                 "ou_pre_avg_over": o, "ou_pre_avg_under": u, "ou_pre_avg_source": "synthetic",
                                 "ou_close_avg_over": o, "ou_close_avg_under": u,
                                 "true_p_over": float(p_over25_poisson(lh_t + la_t))})
    df = pd.DataFrame(rows)
    df["kickoff_time_uk"] = df["kickoff_time_uk"].astype("string")
    df["total_goals"] = df["fthg"] + df["ftag"]
    df["over25"] = (df["total_goals"] > 2.5).astype(float)
    key = df["div"] + "|" + df["match_date"].dt.strftime("%Y-%m-%d") + "|" + df["home_team"] + "|" + df["away_team"]
    df["match_id"] = key.map(lambda k: "syn" + hashlib.sha1(k.encode()).hexdigest()[:13])
    df = temporal.add_temporal_fields(df)
    df["duplicate_key"] = df["match_id"].duplicated(keep=False)
    df["partition"] = "dev"
    for c in ["ou_pre_b365_over", "ou_pre_b365_under", "ou_pre_pin_over", "ou_pre_pin_under", "ou_close_b365_over",
              "ou_close_b365_under", "ou_close_pin_over", "ou_close_pin_under", "ou_pre_max_over", "ou_pre_max_under",
              "ou_close_max_over", "ou_close_max_under", "ou_pre_gb_over", "ou_pre_gb_under"]:
        df[c] = np.nan
    return df.sort_values(["match_date", "div", "home_team"]).reset_index(drop=True)

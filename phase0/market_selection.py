"""Fase Cero — matriz de selección de mercado, análisis de sensibilidad y criterios
secundarios empíricos (potencia estadística y compatibilidad con cuota máx. 3,50).

Entradas:
  configs/market_selection_matrix.json  (puntajes, tipos de evidencia, justificaciones)
  data/raw/football_data/*/data.zip     (solo CUOTAS; no se usan resultados)
Salidas:
  reports/phase0/market_selection_results.json
  reports/phase0/market_selection_tables.md

Semilla fija para reproducibilidad. No entrena modelos ni usa resultados de partidos.
Uso: python phase0/market_selection.py
"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "configs" / "market_selection_matrix.json"
RAW = ROOT / "data" / "raw" / "football_data"
OUT = ROOT / "reports" / "phase0"
SEED = 20261127
N_DRAWS = 20_000
CRIT = ["C1", "C2", "C3", "C4", "C5", "C6"]
Z_ALPHA, Z_BETA = 1.6449, 0.8416  # unilateral alfa=0,05; potencia=0,80


def load():
    cfg = json.loads(CFG.read_text())
    w = np.array([cfg["criteria"][c]["weight"] for c in CRIT])
    keys = list(cfg["markets"])
    S = np.array([[cfg["markets"][k][c][0] for c in CRIT] for k in keys], dtype=float)
    T = np.array([[cfg["markets"][k][c][1] for c in CRIT] for k in keys])
    labels = [cfg["markets"][k]["label"] for k in keys]
    eligible = S[:, 0] >= 2
    return cfg, w, keys, labels, S, T, eligible


def rank_first(scores: np.ndarray, eligible: np.ndarray) -> int:
    s = np.where(eligible, scores, -np.inf)
    return int(np.argmax(s))


def top_k(scores, eligible, k=3):
    s = np.where(eligible, scores, -np.inf)
    return [int(i) for i in np.argsort(-s)[:k]]


def renorm_shift(w, i, delta):
    w2 = w.copy()
    new_i = min(max(w[i] + delta, 0.0), 1.0)
    rest = 1 - w[i]
    w2 = w * (1 - new_i) / rest
    w2[i] = new_i
    return w2


def sensitivity(w, S, T, eligible, keys):
    rng = np.random.default_rng(SEED)
    res = {}
    base = S @ w
    res["base_scores"] = {keys[i]: round(float(base[i]), 4) for i in range(len(keys))}
    res["base_top1"] = keys[rank_first(base, eligible)]
    res["base_top3"] = [keys[i] for i in top_k(base, eligible)]
    # Empates exactos
    ties = [keys[i] for i in range(len(keys)) if eligible[i] and abs(base[i] - base.max()) < 1e-9]
    res["base_ties_at_top"] = ties

    oat = []
    for i, c in enumerate(CRIT):
        for d in (-0.10, -0.05, 0.05, 0.10):
            w2 = renorm_shift(w, i, d)
            sc = S @ w2
            oat.append({"criterion": c, "delta": d, "top1": keys[rank_first(sc, eligible)],
                        "top3": [keys[j] for j in top_k(sc, eligible)],
                        "gap_ou_minus_1x2": round(float(sc[keys.index("FUT_OU25")] - sc[keys.index("FUT_1X2")]), 4)})
    res["one_at_a_time"] = oat
    eq = S @ (np.ones(6) / 6)
    res["equal_weights"] = {"top1": keys[rank_first(eq, eligible)], "top3": [keys[j] for j in top_k(eq, eligible)],
                            "scores": {keys[i]: round(float(eq[i]), 4) for i in range(len(keys))}}

    def freq(draw_scores):
        first = np.zeros(len(keys))
        top3 = np.zeros(len(keys))
        for sc in draw_scores:
            first[rank_first(sc, eligible)] += 1
            for j in top_k(sc, eligible):
                top3[j] += 1
        n = len(draw_scores)
        return ({keys[i]: round(first[i] / n, 4) for i in range(len(keys)) if first[i]},
                {keys[i]: round(top3[i] / n, 4) for i in range(len(keys)) if top3[i]})

    for k in (100, 20):
        W = rng.dirichlet(w * k, size=N_DRAWS)
        f1, f3 = freq(W @ S.T)
        res[f"dirichlet_k{k}"] = {"p_top1": f1, "p_top3": f3}
    # Perturbación de celdas no empíricas (T, J, ND) +-0,5
    soft = np.isin(T, ["T", "J", "ND"])
    draws = []
    for _ in range(N_DRAWS):
        S2 = np.clip(S + soft * rng.uniform(-0.5, 0.5, size=S.shape), 0, 5)
        draws.append(S2 @ w)
    f1, f3 = freq(draws)
    res["perturb_nonempirical_cells"] = {"p_top1": f1, "p_top3": f3}
    draws = []
    W = rng.dirichlet(w * 20, size=N_DRAWS)
    for n in range(N_DRAWS):
        S2 = np.clip(S + soft * rng.uniform(-0.5, 0.5, size=S.shape), 0, 5)
        draws.append(S2 @ W[n])
    f1, f3 = freq(draws)
    res["combined_dirichlet_k20_and_perturb"] = {"p_top1": f1, "p_top3": f3}
    return res


def odds_frame():
    """Cuotas de cierre Bet365 (2019/20+) para O/U 2,5 y 1X2. NO usa resultados."""
    rows_ou, rows_x = [], []
    for z in sorted(RAW.glob("*/data.zip")):
        season = z.parent.name
        if season < "1920":
            continue
        with zipfile.ZipFile(z) as zf:
            for name in zf.namelist():
                df = pd.read_csv(io.StringIO(zf.read(name).decode("latin-1")), dtype=str)
                g = lambda c: pd.to_numeric(df.get(c), errors="coerce")
                o, u = g("B365C>2.5"), g("B365C<2.5")
                m = (o >= 1.01) & (u >= 1.01)
                rows_ou.append(pd.DataFrame({"season": season, "div": name[:-4], "o": o[m], "u": u[m]}))
                h, d, a = g("B365CH"), g("B365CD"), g("B365CA")
                m = (h >= 1.01) & (d >= 1.01) & (a >= 1.01)
                rows_x.append(pd.DataFrame({"season": season, "div": name[:-4], "h": h[m], "d": d[m], "a": a[m]}))
    return pd.concat(rows_ou, ignore_index=True), pd.concat(rows_x, ignore_index=True)


def secondary(ou: pd.DataFrame, x: pd.DataFrame, cap=3.50):
    def per_outcome(Q: np.ndarray):
        inv = 1 / Q
        p = inv / inv.sum(axis=1, keepdims=True)  # normalización proporcional
        Qf, pf = Q.ravel(), p.ravel()
        ok = Qf <= cap
        sd = Qf * np.sqrt(pf * (1 - pf))
        return {
            "n_events": int(Q.shape[0]),
            "n_outcome_prices": int(Qf.size),
            "share_prices_le_cap": round(float(ok.mean()), 4),
            "median_overround": round(float(np.median(inv.sum(axis=1) - 1)), 4),
            "rms_return_sd_per_unit_le_cap": round(float(np.sqrt(np.mean(sd[ok] ** 2))), 4),
            "median_price_le_cap": round(float(np.median(Qf[ok])), 3),
        }

    out = {"cap": cap,
           "FUT_OU25": per_outcome(ou[["o", "u"]].to_numpy()),
           "FUT_1X2": per_outcome(x[["h", "d", "a"]].to_numpy())}
    for k in ("FUT_OU25", "FUT_1X2"):
        sd = out[k]["rms_return_sd_per_unit_le_cap"]
        need = {}
        for roi in (0.01, 0.02, 0.03, 0.05):
            n = ((Z_ALPHA + Z_BETA) * sd / roi) ** 2
            need[f"roi_{roi:.2f}"] = {"bets": int(np.ceil(n)),
                                      **{f"years_at_{b}_per_week": round(n / (b * 52), 1) for b in (5, 10, 20)}}
        out[k]["bets_needed_one_sided_a05_power80_independent"] = need
    return out


def md_table(cfg, keys, labels, S, T, w, eligible, base):
    lines = ["| Mercado | " + " | ".join(f"{c} ({int(w[i]*100)}%)" for i, c in enumerate(CRIT)) + " | Total | Elegible |",
             "|---|" + "---:|" * 6 + "---:|:---:|"]
    order = np.argsort(-base)
    for i in order:
        cells = " | ".join(f"{S[i,j]:g} [{T[i,j]}]" for j in range(6))
        lines.append(f"| {labels[i]} | {cells} | **{base[i]:.3f}** | {'Sí' if eligible[i] else 'No'} |")
    return "\n".join(lines)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cfg, w, keys, labels, S, T, eligible = load()
    assert abs(w.sum() - 1) < 1e-9
    sens = sensitivity(w, S, T, eligible, keys)
    ou, x = odds_frame()
    sec = secondary(ou, x)
    base = S @ w
    res = {"seed": SEED, "n_draws": N_DRAWS, "weights": dict(zip(CRIT, w.tolist())),
           "eligible": {keys[i]: bool(eligible[i]) for i in range(len(keys))},
           "sensitivity": sens, "secondary_empirical_ou_vs_1x2": sec}
    (OUT / "market_selection_results.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
    (OUT / "market_selection_tables.md").write_text(md_table(cfg, keys, labels, S, T, w, eligible, base) + "\n")
    print(md_table(cfg, keys, labels, S, T, w, eligible, base))
    print(json.dumps({k: v for k, v in sens.items() if k != "one_at_a_time"}, indent=1, ensure_ascii=False))
    print("OAT top1 changes:", sorted({(o["criterion"], o["delta"], o["top1"]) for o in sens["one_at_a_time"]}))
    print(json.dumps(sec, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

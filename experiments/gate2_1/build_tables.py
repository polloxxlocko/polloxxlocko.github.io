"""Tablas de GATE 2.1 generadas desde los JSON de resultados (evita transcribir cifras a mano).

Uso: python experiments/gate2_1/build_tables.py --repro experiments/gate2_1/repro_run
Salida: reports/gate2_1/TABLES.md
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def f(x, d=5):
    if x is None:
        return "—"
    if isinstance(x, bool):
        return "sí" if x else "no"
    if isinstance(x, (int,)) and not isinstance(x, bool):
        return f"{x:,}".replace(",", ".")
    s = f"{x:+.{d}f}" if abs(x) < 1 else f"{x:.{d}f}"
    return s.replace(".", ",")


def pr(x):
    return "—" if x is None else f"{x:.3f}".replace(".", ",")


def g(x):
    return "—" if x is None else f"{x:.2e}".replace(".", ",")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repro", required=True)
    a = ap.parse_args()
    rep = Path(a.repro).resolve()
    R = json.loads((rep / "results.json").read_text())
    E = R["evaluate"]
    P = json.loads((ROOT / "experiments" / "gate2" / "results.json").read_text())["evaluate"]
    L = []
    L.append("# Tablas de GATE 2.1 (generadas por experiments/gate2_1/build_tables.py)\n")
    L.append(f"Fuente: `{rep.relative_to(ROOT)}/results.json` (ejecución limpia) y `experiments/gate2/results.json` "
             f"(publicado). n = {f(E['n_primary'])} filas en la prueba interna.\n")
    L.append("## T1. Prueba interna: método publicado (semanas activas) frente a método corregido (semanas calendario), bloque 4\n")
    L.append("| Comparación | Δ̄ | IC publicado | Cat. | IC reproducido, mismo método | Cat. | IC calendario (principal) | Cat. |")
    L.append("|---|---|---|---|---|---|---|---|")
    for k, v in E["comparisons"].items():
        pub = P["comparisons"][k]
        leg = E["comparisons_gate2_method_active_weeks"][k]
        L.append(f"| {k} | {f(v['delta_logloss']['mean'])} | [{f(pub['delta_logloss']['lo'])}; {f(pub['delta_logloss']['hi'])}] | "
                 f"{pub['category']} | [{f(leg['delta_logloss']['lo'])}; {f(leg['delta_logloss']['hi'])}] | {leg['category']} | "
                 f"[{f(v['delta_logloss']['lo'])}; {f(v['delta_logloss']['hi'])}] | **{v['category']}** |")
    L.append("\n## T2. Sensibilidad al bloque (2, 4, 8, 12 semanas) y a la definición de semana\n")
    L.append("| Comparación | Δ̄ | calendario 2 | 4 | 8 | 12 | activas 2 | 4 | 8 | 12 | Categorías | ACF semanal r1, r2, r4 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for k, v in E["block_sensitivity"].items():
        rows = {(r["week_mode"], r["block_weeks"]): r for r in v["rows"]}
        cells = []
        for m in ("calendar", "active"):
            for b in (2, 4, 8, 12):
                r = rows[(m, b)]
                cells.append(f"[{f(r['lo'])}; {f(r['hi'])}] {r['category']}")
        ac = v["weekly_autocorr_calendar_lags1_8"]
        L.append(f"| {k} | {f(v['mean'])} | " + " | ".join(cells) + f" | {', '.join(v['categories'])} | "
                 f"{f(ac[0], 2)}, {f(ac[1], 2)}, {f(ac[3], 2)} |")
    L.append("\n## T3. Decisiones de la escalera (bloque de ajuste) según bloque y definición de semana\n")
    L.append("| Decisión | Filas (modo, bloque → IC, categoría, U < 0) | ¿Estable? |")
    L.append("|---|---|---|")
    for k, v in E["ladder_decision_sensitivity"].items():
        cells = "; ".join(f"{r['week_mode'][:3]} {r['block_weeks']}: [{f(r['lo'])}; {f(r['hi'])}] {r['category']} "
                          f"{'sí' if r['decision_hi_lt_0'] else 'no'}" for r in v["rows"])
        L.append(f"| {k} | {cells} | {f(v['decision_stable'])} |")
    L.append("\n## T4. Potencia en el holdout: superioridad frente a equivalencia (δ = 0,001)\n")
    pw = E["power"]
    L.append(f"N elegible (nivel 0) = {f(pw['n_holdout_eligible_level0'])}. {pw['method']}\n")
    L.append("| Comparación | se desarrollo | se holdout | MDE superioridad vs 0 | Mejora real necesaria para S-R | "
             "P(IC ⊂ (−δ, δ) si θ = 0) | Máx. θ con equivalencia al 80% | se necesario para equivalencia |")
    L.append("|---|---|---|---|---|---|---|---|")
    for k in ("M4sport-M4cal", "M4sport-A", "M4cal-A", "M2-A"):
        r = pw[k]
        pp = r.get("profile_holdout") or {}
        L.append(f"| {k} | {g(r['se_dev'])} | {g(pp.get('se'))} | {g(pp.get('mde_superiority_vs_zero'))} | "
                 f"{g(pp.get('mde_superiority_relevant'))} | {pr(pp.get('p_equivalence_at_zero'))} | "
                 f"{g(pp.get('max_theta_equivalence'))} | {g(pp.get('se_needed_equivalence'))} |")
    L.append("\n## T5. Cobertura del universo de la prueba interna\n")
    L.append("| Pronóstico | Esperadas | Cubiertas | Faltantes | Sobrantes |")
    L.append("|---|---|---|---|---|")
    for k, c in E["coverage"].items():
        L.append(f"| {k} | {f(c['expected'])} | {f(c['covered'])} | {f(c['missing'])} | {f(c['extra'])} |")
    if "m3_spec_sensitivity" in R:
        m = R["m3_spec_sensitivity"]
        L.append("\n## T6. Sensibilidad D-3 (M3 con log(1 + partidos previos), solo bloque de ajuste)\n")
        h = m["H1b_log1p"]["delta_logloss"]
        d = m["selected_log1p_minus_linear_tuning"]["delta_logloss"]
        L.append(f"- M3 seleccionado con log1p: `{m['M3log_selected']}` (lineal: `{m['M3_selected_linear']}`; "
                 f"misma configuración salvo la transformación: {f(m['same_selection_up_to_transform'])}).")
        L.append(f"- H1b con log1p (tiros frente a goles): {f(h['mean'])} [{f(h['lo'])}; {f(h['hi'])}] "
                 f"{m['H1b_log1p']['category']} → los tiros entran en M4-sport: {f(m['shots_enter_M4_sport_log1p'])} "
                 f"(con la forma lineal: {f(m['shots_enter_M4_sport_linear'])}; decisión sin cambios: {f(m['H1b_decision_unchanged'])}).")
        L.append(f"- M3* log1p − M3* lineal (bloque de ajuste): {f(d['mean'])} [{f(d['lo'])}; {f(d['hi'])}] "
                 f"{m['selected_log1p_minus_linear_tuning']['category']}.")
    cc = ROOT / "experiments" / "gate2_1" / "convergence_check.json"
    if cc.exists():
        s = json.loads(cc.read_text())["summary"]
        L.append("\n## T7. Verificación de los ajustes no convergentes\n")
        L.append(f"- Ajustes no convergentes publicados: {s['n_nonconverged_published']}; verificados uno a uno: {s['n_checked']} "
                 f"({s['n_chains']} cadenas configuración-bloque-división).")
        L.append(f"- Cadenas con predicciones idénticas bit a bit a las publicadas: {s['chains_predictions_bitwise_equal']}/{s['n_chains']}; "
                 f"con el mismo conjunto de ajustes no convergentes: {s['chains_same_nonconverged_set']}/{s['n_chains']}.")
        L.append(f"- Criterio estricto: {s['strict_criterion']}. Alcanzado en {s['fits_strict_reached']}/{s['n_checked']}.")
        import pandas as pd
        F = pd.read_csv(ROOT / "experiments" / "gate2_1" / "convergence_check_fits.csv")
        r = F[F["reproduced_as_nonconverged"]]
        L.append(f"- Gradiente residual de la solución publicada (casos reproducidos, n = {len(r)}): "
                 f"{g(r['gmax_std'].min())}-{g(r['gmax_std'].max())}; tras pulir (226 casos): "
                 f"{g(s['gmax_strict']['min'])}-{g(s['gmax_strict']['max'])}.")
        o = s["objective_diff_f_std_minus_f_strict"]
        L.append(f"- f(θ publicado) − f(θ estricto): mín {g(o['min'])}, mediana {g(o['median'])}, máx {g(o['max'])}; max|Δθ| = {g(s['dtheta_max'])}.")
        L.append(f"- Filas predichas por esos ajustes: {f(s['rows_predicted_by_nonconverged_fits'])}; |Δp| máx = {g(s['max_abs_dp'])}, "
                 f"medio = {g(s['mean_abs_dp_over_rows'])}.")
        L.append(f"- Impacto en log loss: suma total {g(s['dlogloss_sum_total'])} nats; máximo impacto en la log loss media de una "
                 f"configuración-bloque: {g(s['max_abs_impact_on_config_block_mean_logloss'])} nats.")
        L.append(f"- Casos no reproducibles o no pulidos: {len(s['unreproducible_or_unpolished_cases'])}.")
    out = ROOT / "reports" / "gate2_1" / "TABLES.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n")
    print(out)


if __name__ == "__main__":
    main()

"""GATE 2.1, exigencia 5: verificación INDIVIDUAL de TODOS los ajustes Poisson marcados como no convergentes
en GATE 2 (sin extrapolar desde una muestra).

Para cada (familia, configuración, bloque, división) con al menos un ajuste no convergente:
1. Se REPRODUCE la cadena walk-forward publicada de esa división (mismo modelo, mismos arranques en caliente).
   Se comprueba que las predicciones coinciden con las publicadas y que los mismos ajustes salen no convergentes.
2. En cada ajuste se toma la solución publicada θ_std y se PULE con pasos de Newton completos (criterio:
   reducir el gradiente) hasta max|∇f| ≤ 1e-10·max(1, Σw), 100 veces más estricto que el criterio de GATE 2
   (1e-8·Σw), o hasta que no haya progreso numérico.
3. Para cada ajuste no convergente se informa: f(θ_std) − f(θ_strict), gradiente residual antes y después,
   max|Δθ|, diferencia máxima y media de probabilidad en las filas que predijo ese ajuste, impacto sobre la log
   loss (suma y media) y sobre la log loss media de la configuración en su bloque, y si el caso es reproducible.
La cadena de estados (arranques en caliente, prior de ascendidos) NO cambia: el pulido solo se usa para
comparar, así que las predicciones estándar deben reproducir exactamente las publicadas.

Uso: python experiments/gate2_1/convergence_check.py   (lee experiments/gate2/ en solo lectura; datos de desarrollo)
Salidas: experiments/gate2_1/convergence_check.json y convergence_check_fits.csv
"""
import json
import os
import sys
import time

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from qsports import evaluation as ev, gate2, models, paths, validation as val, walkforward as wf  # noqa: E402
from qsports.ou import p_over25_poisson  # noqa: E402

PUB = paths.ROOT / "experiments" / "gate2"
OUTD = paths.ROOT / "experiments" / "gate2_1"
STRICT = 1e-10
COLS = ["home_team", "away_team", "fthg", "ftag"]


def polish(th, args, strict=STRICT, max_iter=60):
    nll, hess = models.PoissonModel.nll, models.PoissonModel.hessian
    w = args[4]
    tol = strict * max(1.0, float(w.sum()))
    f, g = nll(th, *args)
    gmax = float(np.max(np.abs(g)))
    it = 0
    while gmax > tol and it < max_iter:
        step = np.linalg.solve(hess(th, *args), -g)
        t, moved = 1.0, False
        while t > 1e-12:
            th_new = th + t * step
            f_new, g_new = nll(th_new, *args)
            gm_new = float(np.max(np.abs(g_new)))
            if np.isfinite(f_new) and gm_new < gmax:
                th, f, g, gmax, moved = th_new, f_new, g_new, gm_new, True
                break
            t *= 0.5
        it += 1
        if not moved:
            break
    return th, f, gmax, it, gmax <= tol, tol


class CheckedPoisson(models.PoissonModel):
    """PoissonModel idéntico al publicado; además guarda la solución pulida para comparar."""

    def newton(self, x0, *args, **kw):  # sombrea el classmethod para capturar θ_std y sus argumentos
        r = models.PoissonModel.newton(x0, *args, **kw)
        self._cap = (r[0].copy(), args)
        return r

    def fit(self, train, tau):
        self._cap = None
        info = super().fit(train, tau)
        self._strict = None
        if self._cap is not None and self.params is not None:
            th, args = self._cap
            f_std, g_std = models.PoissonModel.nll(th, *args)
            th_s, f_s, gm_s, it_s, reached, tol = polish(th, args)
            teams = list(self.params["att"].keys())
            n = len(teams)
            self._strict = {"mu": th_s[0], "eta": th_s[1], "att": dict(zip(teams, th_s[2:2 + n])),
                            "def": dict(zip(teams, th_s[2 + n:]))}
            info.setdefault("extra", {}).update(
                f_std=float(f_std), f_strict=float(f_s), gmax_std=float(np.max(np.abs(g_std))), gmax_strict=gm_s,
                strict_tol=tol, polish_iter=it_s, strict_reached=bool(reached),
                dtheta_max=float(np.max(np.abs(th_s - th))))
        return info

    def predict_extra(self, rows):
        out = super().predict_extra(rows)
        if self.params is None or self._strict is None:
            out["p_strict"] = np.full(len(rows), np.nan)
            return out
        saved = self.params
        self.params = self._strict
        try:
            lh, la = self.intensities(rows)
        finally:
            self.params = saved
        out["p_strict"] = p_over25_poisson(lh + la)
        return out


_G: dict = {}


def _init():
    _G["base"] = gate2.base_frame()
    _G["reg"] = json.loads((PUB / "configs.json").read_text())


def _job(task):
    fam, cid, block, div = task
    base, reg = _G["base"], _G["reg"]
    c = wf.gate2_config()
    seas = c["blocks"]["tuning_seasons_poisson"] if block == "tuning" else c["blocks"]["inner_test_seasons"]
    prm = reg[cid]["params"]
    frame = base[base["div"] == div]
    t0 = time.perf_counter()
    preds, logs = wf.run(frame, lambda: CheckedPoisson(**prm), seas, scope="division", label=cid, n_jobs=1,
                         columns=COLS)
    return task, preds, logs, time.perf_counter() - t0


def main():
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor
    t0 = time.time()
    base = gate2.base_frame()
    y = base.set_index("match_id")["over25"]
    divmap = base.set_index("match_id")["div"]
    tasks, published_nc = [], {}
    for fam in ("M1", "M2"):
        L = pd.read_parquet(PUB / "fitlogs" / f"{fam}.parquet")
        nc = L[~L["converged"]]
        published_nc[fam] = nc
        for (cid, block, div), _ in nc.groupby(["config_id", "block", "scope"]):
            tasks.append((fam, cid, block, div))
    n_nc = sum(len(v) for v in published_nc.values())
    print(f"{n_nc} ajustes no convergentes en {len(tasks)} cadenas (config, bloque, división)", flush=True)
    rows, chains = [], []
    pub_cache: dict = {}
    with ProcessPoolExecutor(4, mp_context=mp.get_context("forkserver"), initializer=_init) as ex:
        for (fam, cid, block, div), preds, logs, wall in ex.map(_job, tasks):
            key = (fam, cid)
            if key not in pub_cache:
                pub_cache[key] = pd.read_parquet(PUB / "predictions" / fam / f"{cid}.parquet")
            P = pub_cache[key]
            Pb = P[(P["block"] == block) & (P["match_id"].map(divmap) == div)]
            m = val.merge_one_to_one(Pb[["match_id", "p_over", "fit_tau"]],
                                     preds[["match_id", "p_over", "p_strict", "fit_tau"]].rename(
                                         columns={"p_over": "p_rep", "fit_tau": "fit_tau_rep"}),
                                     how="inner", context=f"{cid}:{block}:{div}")
            both_nan = m["p_over"].isna() & m["p_rep"].isna()
            same = (m["p_over"] == m["p_rep"]) | both_nan
            reproduced_preds = bool(same.all()) and len(m) == len(Pb) == len(preds)
            ncp = published_nc[fam]
            ncp = ncp[(ncp.config_id == cid) & (ncp.block == block) & (ncp.scope == div)]
            nc_rep = set(logs.loc[~logs["converged"], "fit_tau"])
            chains.append({"family": fam, "config_id": cid, "block": block, "div": div, "fits": int(len(logs)),
                           "rows": int(len(m)), "predictions_bitwise_equal": reproduced_preds,
                           "max_abs_dp_rep_vs_published": float(np.nanmax(np.abs(m["p_rep"] - m["p_over"])))
                           if (~both_nan).any() else 0.0,
                           "nonconverged_published": int(len(ncp)), "nonconverged_replay": int(len(nc_rep)),
                           "same_nonconverged_set": set(ncp["fit_tau"]) == nc_rep, "wall_s": round(wall, 2)})
            ext = logs.set_index("fit_tau")["extra"].map(json.loads)
            n_block = int(y.reindex(P.loc[P["block"] == block, "match_id"]).notna().sum())
            for _, r in ncp.iterrows():
                e = ext.get(r["fit_tau"], {})
                mm = m[(m["fit_tau_rep"].astype(str).str[:10] == r["fit_tau"])].copy()
                mm["y"] = mm["match_id"].map(y)
                mm = mm[mm["y"].notna() & mm["p_over"].notna()]
                dp = (mm["p_strict"] - mm["p_over"]).to_numpy()
                dll = (ev.log_loss(mm["y"], mm["p_strict"]) - ev.log_loss(mm["y"], mm["p_over"])) if len(mm) else np.array([])
                rows.append({"family": fam, "config_id": cid, "block": block, "div": div, "fit_tau": r["fit_tau"],
                             "published_message": r["message"], "n_train": int(r["n_train"]),
                             "reproduced_as_nonconverged": r["fit_tau"] in nc_rep,
                             "f_std_minus_f_strict": e.get("f_std", np.nan) - e.get("f_strict", np.nan),
                             "f_std": e.get("f_std"), "gmax_std": e.get("gmax_std"), "gmax_strict": e.get("gmax_strict"),
                             "strict_tol": e.get("strict_tol"), "strict_reached": e.get("strict_reached"),
                             "polish_iter": e.get("polish_iter"), "dtheta_max": e.get("dtheta_max"),
                             "rows_predicted": int(len(mm)),
                             "max_abs_dp": float(np.max(np.abs(dp))) if len(dp) else 0.0,
                             "mean_abs_dp": float(np.mean(np.abs(dp))) if len(dp) else 0.0,
                             "dlogloss_sum": float(dll.sum()) if len(dll) else 0.0,
                             "dlogloss_mean_rows": float(dll.mean()) if len(dll) else 0.0,
                             "impact_on_config_block_mean_logloss": float(dll.sum() / n_block) if n_block else np.nan})
    F = pd.DataFrame(rows)
    C = pd.DataFrame(chains)
    OUTD.mkdir(parents=True, exist_ok=True)
    F.to_csv(OUTD / "convergence_check_fits.csv", index=False)
    unrepro = F[~F["reproduced_as_nonconverged"] | ~F["strict_reached"].astype(bool)]
    summ = {
        "n_nonconverged_published": int(n_nc), "n_checked": int(len(F)), "n_chains": int(len(C)),
        "strict_criterion": f"max|grad| <= {STRICT:g}·max(1, Σw)  (GATE 2: 1e-8·max(1, Σw))",
        "chains_predictions_bitwise_equal": int(C["predictions_bitwise_equal"].sum()),
        "chains_same_nonconverged_set": int(C["same_nonconverged_set"].sum()),
        "fits_reproduced_as_nonconverged": int(F["reproduced_as_nonconverged"].sum()),
        "fits_strict_reached": int(F["strict_reached"].astype(bool).sum()),
        "objective_diff_f_std_minus_f_strict": {"min": float(F["f_std_minus_f_strict"].min()),
                                                "max": float(F["f_std_minus_f_strict"].max()),
                                                "median": float(F["f_std_minus_f_strict"].median())},
        "gmax_std": {"min": float(F["gmax_std"].min()), "max": float(F["gmax_std"].max())},
        "gmax_strict": {"min": float(F["gmax_strict"].min()), "max": float(F["gmax_strict"].max())},
        "dtheta_max": float(F["dtheta_max"].max()),
        "max_abs_dp": float(F["max_abs_dp"].max()), "mean_abs_dp_over_rows": float(
            (F["mean_abs_dp"] * F["rows_predicted"]).sum() / max(F["rows_predicted"].sum(), 1)),
        "rows_predicted_by_nonconverged_fits": int(F["rows_predicted"].sum()),
        "dlogloss_sum_total": float(F["dlogloss_sum"].sum()),
        "max_abs_impact_on_config_block_mean_logloss": float(F.groupby(["config_id", "block"])[
            "impact_on_config_block_mean_logloss"].sum().abs().max()),
        "unreproducible_or_unpolished_cases": unrepro[["family", "config_id", "block", "div", "fit_tau",
                                                       "reproduced_as_nonconverged", "strict_reached",
                                                       "gmax_strict", "strict_tol"]].to_dict("records"),
        "chains_not_bitwise_equal": C[~C["predictions_bitwise_equal"]].to_dict("records"),
        "by_family": F.groupby("family").agg(n=("fit_tau", "size"), max_abs_dp=("max_abs_dp", "max"),
                                             dlogloss_sum=("dlogloss_sum", "sum")).reset_index().to_dict("records"),
        "wall_s": round(time.time() - t0, 1),
        "script_sha256": gate2.sha256_file(__import__("pathlib").Path(__file__)),
        "code_hash": gate2.code_hash(),
    }
    (OUTD / "convergence_check.json").write_text(json.dumps({"summary": summ, "chains": C.to_dict("records")},
                                                            indent=1, ensure_ascii=False, default=float))
    print(json.dumps({k: v for k, v in summ.items() if k not in ("unreproducible_or_unpolished_cases",
                                                                 "chains_not_bitwise_equal")}, indent=1, default=float))
    print("casos no reproducibles o no pulidos:", len(unrepro))
    return 0


if __name__ == "__main__":
    sys.exit(main())

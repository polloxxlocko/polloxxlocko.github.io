"""Modelos de la escalera GATE 2 (ver MODEL_SPECIFICATION.md §A3).

Interfaz común (motor walk-forward):
    fit(train, tau) -> dict(converged, iterations, message)    # train: solo filas con match_date < tau
    predict(rows) -> np.ndarray P(Over 2,5)                     # rows: solo columnas pre-partido
Toda transformación (estandarización, imputación, priors) se ajusta en `fit` con filas de
entrenamiento. La predicción de una fila no depende de otras filas del lote, salvo la
identificación de equipos actuales para el prior de equipos nuevos (M2 etapa 2), que usa
solo el calendario: información pre-partido.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import optimize

from .odds import inv_logit, logit
from .ou import p_over25_poisson

LN2 = math.log(2.0)


def _season_codes(tau: pd.Timestamp) -> tuple[str, str]:
    y = tau.year if tau.month >= 7 else tau.year - 1
    cur = f"{y % 100:02d}{(y + 1) % 100:02d}"
    prev = f"{(y - 1) % 100:02d}{y % 100:02d}"
    return cur, prev


# ---------------------------------------------------------------- M0a
class FreqModel:
    """Frecuencia histórica de Over por división, (k+1)/(n+2), con ventana opcional (días)."""

    def __init__(self, window_days: int | None = None):
        self.window_days = window_days

    def fit(self, train, tau):
        t = train[train["over25"].notna()]
        if self.window_days:
            t = t[(tau - t["match_date"]).dt.days < self.window_days]
        self.p = (t["over25"].sum() + 1) / (len(t) + 2)
        return {"converged": True, "iterations": 0}

    def predict(self, rows):
        return np.full(len(rows), self.p)


# ---------------------------------------------------------------- M1 / M2
class PoissonModel:
    """Poisson independiente por división con ridge. Ventana (M1) o decaimiento exponencial (M2)."""

    def __init__(self, window_days: int | None = None, half_life_days: float | None = None, ridge: float = 4.0,
                 max_history_days: int = 1460, promoted_prior: bool = False):
        if (window_days is None) == (half_life_days is None):
            raise ValueError("Especifique window_days (M1) o half_life_days (M2)")
        self.window_days, self.half_life_days = window_days, half_life_days
        self.ridge, self.max_history_days, self.promoted_prior = ridge, max_history_days, promoted_prior
        self._last: dict[str, tuple[float, float]] = {}
        self.params = None

    # -- verosimilitud penalizada y gradiente analítico
    @staticmethod
    def nll(theta, hi, ai, yh, ya, w, n, ridge, m_att, m_def):
        mu, eta = theta[0], theta[1]
        att, dfn = theta[2:2 + n], theta[2 + n:]
        lh = np.exp(mu + eta + att[hi] - dfn[ai])
        la = np.exp(mu + att[ai] - dfn[hi])
        f = np.sum(w * (lh - yh * np.log(lh) + la - ya * np.log(la)))
        f += 0.5 * ridge * (np.sum((att - m_att) ** 2) + np.sum((dfn - m_def) ** 2))
        rh, ra = w * (lh - yh), w * (la - ya)
        g = np.empty_like(theta)
        g[0] = rh.sum() + ra.sum()
        g[1] = rh.sum()
        g[2:2 + n] = np.bincount(hi, rh, n) + np.bincount(ai, ra, n) + ridge * (att - m_att)
        g[2 + n:] = -np.bincount(ai, rh, n) - np.bincount(hi, ra, n) + ridge * (dfn - m_def)
        return f, g

    @staticmethod
    def hessian(theta, hi, ai, yh, ya, w, n, ridge, m_att, m_def):
        """Hessiana analítica de la NLL penalizada (definida positiva si ridge > 0)."""
        mu, eta = theta[0], theta[1]
        att, dfn = theta[2:2 + n], theta[2 + n:]
        lh = w * np.exp(mu + eta + att[hi] - dfn[ai])
        la = w * np.exp(mu + att[ai] - dfn[hi])
        m = len(hi)
        p = 2 + 2 * n
        r = np.arange(m)
        Xh = np.zeros((m, p)); Xa = np.zeros((m, p))
        Xh[:, 0] = 1; Xh[:, 1] = 1; Xh[r, 2 + hi] = 1; Xh[r, 2 + n + ai] = -1
        Xa[:, 0] = 1; Xa[r, 2 + ai] = 1; Xa[r, 2 + n + hi] = -1
        H = (Xh * lh[:, None]).T @ Xh + (Xa * la[:, None]).T @ Xa
        H[np.arange(2, p), np.arange(2, p)] += ridge
        return H

    @classmethod
    def newton(cls, x0, hi, ai, yh, ya, w, n, ridge, m_att, m_def, tol=1e-8, max_iter=100):
        """Newton-Raphson amortiguado (búsqueda lineal de Armijo). Problema estrictamente convexo con ridge > 0."""
        args = (hi, ai, yh, ya, w, n, ridge, m_att, m_def)
        th = x0.copy()
        f, g = cls.nll(th, *args)
        for it in range(1, max_iter + 1):
            gmax = float(np.max(np.abs(g)))
            if gmax < tol * max(1.0, float(w.sum())):
                return th, it - 1, gmax, True, "ok"
            H = cls.hessian(th, *args)
            try:
                step = np.linalg.solve(H, -g)
            except np.linalg.LinAlgError:
                return th, it, gmax, False, "hessiana singular"
            t_, dec = 1.0, float(g @ step)
            while True:
                th_new = th + t_ * step
                f_new, g_new = cls.nll(th_new, *args)
                if np.isfinite(f_new) and f_new <= f + 1e-4 * t_ * dec:
                    break
                t_ *= 0.5
                if t_ < 1e-10:
                    return th, it, gmax, False, "búsqueda lineal fallida"
            th, f, g = th_new, f_new, g_new
        return th, max_iter, float(np.max(np.abs(g))), False, "max_iter"

    def _weights(self, age):
        if self.window_days is not None:
            return (age < self.window_days).astype(float)
        return np.where(age < self.max_history_days, np.exp(-LN2 * age / self.half_life_days), 0.0)

    def fit(self, train, tau):
        t = train[train["fthg"].notna() & train["ftag"].notna()]
        age = (tau - t["match_date"]).dt.days.to_numpy()
        w = self._weights(age)
        t, w = t[w > 0], w[w > 0]
        self._cur, self._prev = _season_codes(tau)
        self._teams_prev = set(t.loc[t["season_code"] == self._prev, "home_team"]) | set(
            t.loc[t["season_code"] == self._prev, "away_team"])
        self._teams_cur = set(t.loc[t["season_code"] == self._cur, "home_team"]) | set(
            t.loc[t["season_code"] == self._cur, "away_team"])
        if len(t) == 0:
            self.params = None
            return {"converged": True, "iterations": 0, "message": "sin datos"}
        teams = sorted(set(t["home_team"]) | set(t["away_team"]))
        ix = {k: i for i, k in enumerate(teams)}
        n = len(teams)
        hi = t["home_team"].map(ix).to_numpy()
        ai = t["away_team"].map(ix).to_numpy()
        m_att, m_def = np.zeros(n), np.zeros(n)
        self._new_prior = (0.0, 0.0)
        if self.promoted_prior and self._last:
            departed = self._teams_prev - self._teams_cur if self._teams_cur else set()
            dep = [self._last[k] for k in sorted(departed) if k in self._last]  # orden fijo: determinista
            if dep:
                self._new_prior = (float(np.mean([d[0] for d in dep])), float(np.mean([d[1] for d in dep])))
                for k in self._teams_cur - self._teams_prev:
                    m_att[ix[k]], m_def[ix[k]] = self._new_prior
        x0 = np.zeros(2 + 2 * n)
        if self.params is not None:
            x0[0], x0[1] = self.params["mu"], self.params["eta"]
            for k, i in ix.items():
                if k in self.params["att"]:
                    x0[2 + i], x0[2 + n + i] = self.params["att"][k], self.params["def"][k]
        else:
            x0[0] = math.log(max(np.average(t[["fthg", "ftag"]].to_numpy().mean(axis=1), weights=w), 0.1))
        th, it, gnorm, ok, msg = self.newton(x0, hi, ai, t["fthg"].to_numpy(), t["ftag"].to_numpy(), w, n,
                                             self.ridge, m_att, m_def)
        self.params = {"mu": th[0], "eta": th[1], "att": dict(zip(teams, th[2:2 + n])),
                       "def": dict(zip(teams, th[2 + n:]))}
        self._last = {k: (self.params["att"][k], self.params["def"][k]) for k in teams}
        return {"converged": ok, "iterations": it, "message": f"gmax={gnorm:.2e} {msg}",
                "extra": {"mu": float(th[0]), "eta": float(th[1]), "n_teams": n, "gmax": gnorm,
                          "new_prior_att": float(self._new_prior[0]), "new_prior_def": float(self._new_prior[1])}}

    def _team(self, name, rows_teams):
        if name in self.params["att"]:
            return self.params["att"][name], self.params["def"][name]
        if self.promoted_prior and self._last and not self._teams_cur:
            departed = self._teams_prev - rows_teams
            dep = [self._last[k] for k in sorted(departed) if k in self._last]  # orden fijo: determinista
            if dep:
                return float(np.mean([d[0] for d in dep])), float(np.mean([d[1] for d in dep]))
        return self._new_prior if self.promoted_prior else (0.0, 0.0)

    def intensities(self, rows):
        rows_teams = set(rows["home_team"]) | set(rows["away_team"])
        mu, eta = self.params["mu"], self.params["eta"]
        h = np.array([self._team(k, rows_teams) for k in rows["home_team"]])
        a = np.array([self._team(k, rows_teams) for k in rows["away_team"]])
        lh = np.exp(mu + eta + h[:, 0] - a[:, 1])
        la = np.exp(mu + a[:, 0] - h[:, 1])
        return lh, la

    def predict(self, rows):
        if self.params is None:
            return np.full(len(rows), np.nan)
        lh, la = self.intensities(rows)
        return p_over25_poisson(lh + la)

    def predict_extra(self, rows):
        if self.params is None:
            return {"lam_h": np.full(len(rows), np.nan), "lam_a": np.full(len(rows), np.nan)}
        lh, la = self.intensities(rows)
        return {"lam_h": lh, "lam_a": la}


# ---------------------------------------------------------------- regresión logística ridge
def fit_logistic(X, y, w, penalized, lam, x0=None):
    """Minimiza Σ w·logloss + (lam/2)·Σ_{penalizados} β². Devuelve (beta, resultado scipy)."""
    pen = np.asarray(penalized, float)

    def f(b):
        eta = X @ b
        mu = 1 / (1 + np.exp(-eta))
        v = np.sum(w * (np.logaddexp(0, eta) - y * eta)) + 0.5 * lam * np.sum(pen * b * b)
        g = X.T @ (w * (mu - y)) + lam * pen * b
        return v, g

    r = optimize.minimize(f, np.zeros(X.shape[1]) if x0 is None else x0, jac=True, method="L-BFGS-B",
                          options={"maxiter": 2000, "gtol": 1e-7})
    return r.x, r


class _Design:
    """Estandarización + imputación con media de entrenamiento + indicadores de faltante (ajustados en fit)."""

    def __init__(self, cols):
        self.cols = list(cols)

    def fit(self, df):
        X = df[self.cols].astype(float)
        self.mean = X.mean().fillna(0.0)
        Xi = X.fillna(self.mean)
        self.sd = Xi.std(ddof=0).replace(0, 1.0).fillna(1.0)
        self.miss_cols = [c for c in self.cols if X[c].isna().any()]
        return self

    def transform(self, df):
        X = df[self.cols].astype(float)
        Z = ((X.fillna(self.mean) - self.mean) / self.sd).to_numpy()
        M = np.column_stack([X[c].isna().to_numpy(float) for c in self.miss_cols]) if self.miss_cols else np.empty((len(df), 0))
        return np.hstack([Z, M])


# ---------------------------------------------------------------- M3
class LogisticFeatureModel:
    """M3: logit p = β0 + γ·logit(p_C) + βᵀ[features estandarizadas, indicadores]; ridge sobre β."""

    def __init__(self, feature_cols, ridge: float = 10.0, base_col: str = "p_C_hist_freq"):
        self.feature_cols, self.ridge, self.base_col = list(feature_cols), ridge, base_col
        self.beta = None

    def _X(self, df):
        z = logit(np.clip(df[self.base_col].to_numpy(float), 1e-6, 1 - 1e-6))
        return np.column_stack([np.ones(len(df)), z, self.design.transform(df)])

    def fit(self, train, tau):
        t = train[train["over25"].notna() & train[self.base_col].notna()]
        if len(t) < 200:
            self.beta = None
            return {"converged": True, "iterations": 0, "message": "insuficiente"}
        self.design = _Design(self.feature_cols).fit(t)
        X = self._X(t)
        pen = np.r_[0.0, 0.0, np.ones(X.shape[1] - 2)]
        self.beta, r = fit_logistic(X, t["over25"].to_numpy(float), np.ones(len(t)), pen, self.ridge,
                                    x0=self.beta if self.beta is not None and len(self.beta) == X.shape[1] else None)
        return {"converged": bool(r.success), "iterations": int(r.nit), "message": str(r.message)[:60],
                "extra": {"coef_base": [float(x) for x in self.beta[:2]], "n_train_used": int(len(t)),
                          "coef_l2": float(np.sqrt(np.sum(self.beta[2:] ** 2)))}}

    def predict(self, rows):
        if self.beta is None:
            return np.full(len(rows), np.nan)
        return inv_logit(self._X(rows) @ self.beta)


# ---------------------------------------------------------------- M4
class MarketModel:
    """M4-cal (sport_cols=[]): logit p = a + b·logit p_A.
    M4-sport: + βᵀX con X = desviaciones logit(inp) − logit(p_A) estandarizadas; ridge solo sobre β.
    `require_cols`: filas de entrenamiento que deben tener estas columnas (se usa para que M4-cal y
    M4-sport se ajusten EXACTAMENTE sobre las mismas filas)."""

    def __init__(self, sport_cols=(), ridge: float = 100.0, half_life_days: float | None = None,
                 require_cols=(), market_col: str = "p_A_consensus"):
        self.sport_cols, self.ridge, self.half_life_days = list(sport_cols), ridge, half_life_days
        self.require_cols, self.market_col = list(require_cols), market_col
        self.beta = None

    def _raw(self, df):
        pa = np.clip(df[self.market_col].to_numpy(float), 1e-6, 1 - 1e-6)
        zA = logit(pa)
        dev = [logit(np.clip(df[c].to_numpy(float), 1e-6, 1 - 1e-6)) - zA for c in self.sport_cols]
        return zA, (np.column_stack(dev) if dev else np.empty((len(df), 0)))

    def fit(self, train, tau):
        need = [self.market_col, "over25"] + self.sport_cols + self.require_cols
        t = train.dropna(subset=list(dict.fromkeys(need)))
        if len(t) < 200:
            self.beta = None
            return {"converged": True, "iterations": 0, "message": "insuficiente"}
        zA, D = self._raw(t)
        self.mu, self.sd = (D.mean(axis=0), D.std(axis=0) + 1e-12) if D.shape[1] else (None, None)
        X = np.column_stack([np.ones(len(t)), zA] + ([(D - self.mu) / self.sd] if D.shape[1] else []))
        w = np.ones(len(t)) if self.half_life_days is None else np.exp(
            -LN2 * (tau - t["match_date"]).dt.days.to_numpy() / self.half_life_days)
        pen = np.r_[0.0, 0.0, np.ones(D.shape[1])]
        self.beta, r = fit_logistic(X, t["over25"].to_numpy(float), w, pen, self.ridge,
                                    x0=self.beta if self.beta is not None and len(self.beta) == X.shape[1] else
                                    np.r_[0.0, 1.0, np.zeros(D.shape[1])])
        return {"converged": bool(r.success), "iterations": int(r.nit), "message": str(r.message)[:60],
                "extra": {"coef": [float(x) for x in self.beta], "n_train_used": int(len(t))}}

    def predict(self, rows):
        if self.beta is None:
            return np.full(len(rows), np.nan)
        zA, D = self._raw(rows)
        X = np.column_stack([np.ones(len(rows)), zA] + ([(D - self.mu) / self.sd] if D.shape[1] else []))
        return inv_logit(X @ self.beta)


class MarketNull:
    """M4-null = benchmark A."""

    def fit(self, train, tau):
        return {"converged": True, "iterations": 0}

    def predict(self, rows):
        return rows["p_A_consensus"].to_numpy(float)

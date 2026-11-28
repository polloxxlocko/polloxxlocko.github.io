"""Pruebas de integración sobre los datos reales construidos (se omiten si no existen)."""
import numpy as np
import pandas as pd
import pytest

from qsports import benchmark, holdout, paths, process, verify

pytestmark = pytest.mark.skipif(not (paths.PROCESSED_DEV / "matches.parquet").exists(),
                                reason="Requiere python -m qsports build")


@pytest.fixture(scope="module")
def dev():
    return process.load_dev()


@pytest.fixture(scope="module")
def bench():
    return process.load_dev_benchmarks()


def test_dev_only_contains_dev_seasons(dev):
    assert dev.season_code.max() <= paths.holdout_config()["dev_last_season"]
    assert set(dev.partition) == {"dev"}
    assert dev["div"].nunique() == 22


def test_dev_and_reserved_ids_disjoint(dev):
    assert not (set(dev.match_id) & holdout.reserved_ids())


def test_match_ids_unique_and_no_duplicate_keys(dev):
    assert dev.match_id.is_unique
    assert not dev.duplicate_key.any()


def test_schema_core_columns(dev):
    for c in ["match_id", "div", "season_code", "match_date", "home_team", "away_team", "fthg", "ftag", "over25",
              "ou_pre_avg_over", "ou_pre_avg_under", "ou_close_avg_over", "pre_odds_capture_date_est",
              "info_cutoff_date", "kickoff_at_utc", "capture_rule_ambiguous", "source_file", "raw_zip_sha256",
              "home_team_raw"]:
        assert c in dev.columns, c


def test_settlement_consistent(dev):
    r = dev[dev.fthg.notna()]
    assert ((r.fthg + r.ftag > 2.5).astype(float) == r.over25).all()


def test_point_in_time_cutoff(dev):
    d = dev[dev.match_date.notna()]
    lag = (d.match_date - d.info_cutoff_date).dt.days
    assert lag.between(0, 3).all()
    assert (lag[d.weekday.isin([1, 4])] == 0).all()  # martes/viernes: corte = mismo día (excluido)


def test_benchmark_rows_aligned(dev, bench):
    assert (bench.match_id.values == dev.match_id.values).all()


def test_benchmark_probabilities_valid(bench):
    for c in ["p_A_consensus", "p_B_consensus", "p_A_b365", "p_A_pin", "p_C_hist_freq"]:
        v = bench[c].dropna()
        assert ((v > 0) & (v < 1)).all(), c
    ok = bench.A_consensus_valid
    assert bench.loc[ok, "A_consensus_overround"].between(0, 0.25).all()


def test_benchmark_C_matches_bruteforce(dev, bench):
    rng = np.random.default_rng(1)
    idx = rng.choice(dev.index[dev.info_cutoff_date.notna()], size=150, replace=False)
    for i in idx:
        r = dev.loc[i]
        h = dev[(dev["div"] == r["div"]) & (dev.match_date < r.info_cutoff_date) & dev.over25.notna()]
        assert bench.loc[i, "p_C_hist_freq"] == pytest.approx((h.over25.sum() + 1) / (len(h) + 2), abs=1e-12)


def test_no_pinnacle_after_rule_date_in_dev_by_construction(dev):
    # dev termina en 2023/24: la regla de Pinnacle (23/07/2025) no debe afectar a desarrollo
    assert dev.match_date.max() < pd.Timestamp("2025-07-23")


def test_verify_all_ok():
    """Todos los controles de integridad verdaderos; reserva sellada con 0 accesos. El holdout está sellado (0 accesos)
    salvo tras la prueba final autorizada: entonces `ok` es falso solo porque ya no está sellado, y sus accesos deben
    ser coherentes con la autorización vigente."""
    res = verify.verify_all()
    assert all(res["checks"].values()), res["checks"]
    assert res["reserve_sealed"] and res["access_log_entries"]["reserve"] == 0
    if res["holdout_sealed"]:
        assert res["ok"] and res["access_log_entries"]["holdout"] == 0
    else:
        assert res["seal_state"]["holdout"]["ok"]
        assert (paths.ROOT / "logs" / "FINAL_TEST_EVALUATED.json").exists()


# ---------------------------------------------------------------- recomendaciones de la auditoría de GATE 1
def test_alias_integrity_no_merged_distinct_teams(dev):
    """Un alias erróneo que fusionara dos clubes distintos duplicaría apariciones en una temporada."""
    assert not (dev["home_team"] == dev["away_team"]).any()
    t = pd.concat([dev[["div", "season_code", "home_team"]].rename(columns={"home_team": "team"}),
                   dev[["div", "season_code", "away_team"]].rename(columns={"away_team": "team"})])
    n = t.groupby(["div", "season_code", "team"]).size()
    med = n.groupby(level=[0, 1]).transform("median")
    assert (n <= 1.25 * med).all(), n[n > 1.25 * med].head()


def test_alias_config_scope(dev):
    import json
    from qsports import paths as P
    al = json.loads((P.CONFIGS / "team_aliases.json").read_text())["aliases"]
    for country, m in al.items():
        sub = dev[dev["country"] == country]
        raw = set(sub["home_team_raw"]) | set(sub["away_team_raw"])
        canon = set(sub["home_team"]) | set(sub["away_team"])
        for name, v in m.items():
            assert name in raw, (country, name)              # el alias corresponde a un nombre real del país
            assert v["canonical"] in canon and name not in canon
            other = dev[dev["country"] != country]
            assert name not in set(other["home_team_raw"]) | set(other["away_team_raw"])


def test_pre_to_close_movement_gradient_regression(dev, bench):
    """Regresión de la evidencia de la regla de captura: el movimiento pre→cierre crece con los días
    transcurridos desde la captura (vie<sáb<dom<lun; mar<mié). Alarma si la fuente cambia su política."""
    d = dev[(dev.season_code >= "1920")]
    b = bench.loc[d.index]
    m = b.A_consensus_valid & b.B_consensus_valid
    move = (b.p_B_consensus - b.p_A_consensus).abs()[m]
    med = move.groupby(d.weekday[m]).median()
    assert med[4] < med[5] < med[6] < med[0]
    assert med[1] < med[2]

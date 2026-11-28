"""GATE 4: modo autorizado del holdout en el motor y en el universo de evaluación (solo datos sintéticos y un
proyecto temporal con autorización ficticia; el holdout real no se abre)."""
import json

import pytest

from qsports import gate2, holdout, paths, synthetic, walkforward as wf


class Probe:
    def fit(self, train, tau):
        return {}

    def predict(self, rows):
        return [0.5] * len(rows)


@pytest.fixture()
def fake_auth(tmp_path, monkeypatch):
    """Proyecto temporal con protocolo congelado y autorización ficticia del holdout."""
    (tmp_path / "PROTO.md").write_text("protocolo congelado v1")
    (tmp_path / "PROTOCOL_FREEZE.json").write_text(json.dumps({"files": ["PROTO.md"]}))
    monkeypatch.setattr(paths, "ROOT", tmp_path)
    auth = {"partition": "holdout", "authorized_by": "prueba", "authorized_at": "2026-01-01",
            "user_statement": "autorizo (prueba sintética)", "purpose": "prueba",
            "protocol_freeze_sha256": holdout.protocol_freeze_hash()}
    (tmp_path / paths.holdout_config()["authorization_file"]).write_text(json.dumps(auth))
    return holdout.holdout_authorization()


@pytest.fixture(scope="module")
def syn():
    return synthetic.generate(n_divisions=1, n_teams=6, seasons=("2324", "2425"), seed=8)


def test_holdout_rows_rejected_without_authorization(syn, tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "ROOT", tmp_path)
    with pytest.raises(holdout.ReservedDataError):
        wf.run(syn, Probe, ["2425"], label="sin-autorizacion")
    with pytest.raises(holdout.ReservedDataError):
        holdout.holdout_authorization()


def test_authorized_holdout_mode_runs_and_logs(syn, fake_auth):
    p, _ = wf.run(syn, Probe, ["2425"], label="final", holdout_authorization=fake_auth)
    assert len(p) > 0
    ev = [json.loads(x) for x in paths.FENCE_LOG.read_text().splitlines()]
    assert ev[-1]["outcome"] == "allowed-holdout" and ev[-1]["seasons"] == ["2425"]
    assert wf.fence_log_summary()["ok"]


def test_reserve_never_allowed_even_with_holdout_authorization(fake_auth):
    s = synthetic.generate(n_divisions=1, n_teams=6, seasons=("2526", "2627"), seed=9)
    with pytest.raises(holdout.ReservedDataError):
        wf.run(s, Probe, ["2627"], label="reserva", holdout_authorization=fake_auth)
    with pytest.raises(wf.FenceError):
        wf.check_fence(["2627"], "reserva", fake_auth)


def test_tampered_or_stale_authorization_rejected(syn, fake_auth):
    bad = dict(fake_auth, user_statement="otra declaración")
    with pytest.raises(holdout.ReservedDataError):
        wf.run(syn, Probe, ["2425"], label="manipulada", holdout_authorization=bad)
    (paths.ROOT / "PROTO.md").write_text("protocolo modificado después de autorizar")
    with pytest.raises(holdout.ReservedDataError):
        wf.run(syn, Probe, ["2425"], label="protocolo-cambiado", holdout_authorization=fake_auth)


def test_universe_requires_holdout_authorization(syn, fake_auth):
    s = syn.assign(elig=True)
    with pytest.raises(wf.FenceError):
        gate2.universe(s, ["2425"])
    assert len(gate2.universe(s, ["2425"], holdout_authorization=fake_auth)) > 0
    outs = [json.loads(x)["outcome"] for x in paths.FENCE_LOG.read_text().splitlines()]
    assert outs[-2:] == ["refused", "allowed-holdout"]


def test_fence_summary_fails_if_authorization_disappears(syn, fake_auth):
    wf.run(syn, Probe, ["2425"], label="final", holdout_authorization=fake_auth)
    (paths.ROOT / paths.holdout_config()["authorization_file"]).unlink()
    assert not wf.fence_log_summary()["ok"]

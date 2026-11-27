"""Parser tolerante de Football-Data con archivos sintéticos (casos patológicos reales)."""
import zipfile

import numpy as np
import pandas as pd

from qsports import ingest


def _zip(tmp_path, files: dict[str, bytes]):
    z = tmp_path / "data.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for n, b in files.items():
            zf.writestr(n, b)
    return z


def test_rows_wider_than_header_are_recovered_and_aligned(tmp_path):
    csv = ("Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,B365H,B365D,B365A\n"
           "E2,10/08/02,Bristol City,Blackpool,2,0,H,1.6,3.4,4.5\n"
           "E2,04/02/03,Notts County,Crewe,2,2,D,3.25,3.25,2,9.9,9.9\n"   # 2 campos extra
           ",,,,,,,,,\n").encode()
    df, rep = ingest.parse_season_zip(_zip(tmp_path, {"E2.csv": csv}), "0203")
    assert len(df) == 2
    assert rep[0]["rows_wider_than_header"] == 1
    r = df[df.home_team == "Notts County"].iloc[0]
    assert r.fthg == 2 and r.x12_pre_b365_a == 2.0  # alineación conservada
    assert r.match_date == pd.Timestamp("2003-02-04")


def test_aliases_duplicate_headers_encodings_and_regimes(tmp_path):
    greek = ("Div,Date,HT,AT,FTHG,FTAG,FTR,LB,LB,BbAv>2.5,BbAv<2.5\n"
             "G1,20/08/2000,Olympiakos,PAOK,3,1,H,1.2,1.3,1.8,2.0\n").encode("utf-8")
    new = ("﻿Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR,Avg>2.5,Avg<2.5,P>2.5,P<2.5,PSCH\n"
           "E0,12/08/2023,15:00,King’s Lynn,Arsenal,0,1,A,1.9,1.95,1.93,2.0,#REF!\n").encode("utf-8")
    cp = ("Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\nD1,01/09/01,K\xf6ln,Bayern Munich,1,1,D\n").encode("cp1252")
    df, rep = ingest.parse_season_zip(_zip(tmp_path, {"G1.csv": greek, "E0.csv": new, "D1.csv": cp}), "0001")
    g = df[df["div"] == "G1"].iloc[0]
    assert g.home_team == "Olympiakos" and g.ou_pre_avg_source == "betbrain" and g.ou_pre_avg_over == 1.8
    e = df[df["div"] == "E0"].iloc[0]
    assert e.ou_pre_avg_source == "oddsportal" and e.ou_pre_pin_under == 2.0 and e.home_team == "King’s Lynn"
    assert np.isnan(e.x12_close_pin_h)  # '#REF!' -> NaN, registrado
    reps = {r["div"]: r for r in rep}
    assert reps["E0"]["non_numeric_values"]["x12_close_pin_h"] == ["#REF!"]
    assert reps["G1"]["duplicate_header_names"] == ["LB"]
    assert reps["D1"]["encoding"] == "cp1252" and df[df["div"] == "D1"].iloc[0].home_team == "Köln"
    assert reps["E0"]["encoding"] == "utf-8-sig"


def test_match_id_uses_raw_names_and_team_alias_applied(tmp_path):
    csv = "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG\nSC1,23/11/2004,Ross County,Raith,1,0\n".encode()
    df, _ = ingest.parse_season_zip(_zip(tmp_path, {"SC1.csv": csv}), "0405")
    r = df.iloc[0]
    assert r.away_team == "Raith Rvs" and r.away_team_raw == "Raith"
    raw_id = ingest.make_match_id("SC1", pd.Series([pd.Timestamp("2004-11-23")]), pd.Series(["Ross County"]),
                                  pd.Series(["Raith"]))[0]
    assert r.match_id == raw_id


def test_settlement_and_flags(tmp_path):
    csv = ("Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,HTHG,HTAG,HTR,HS,AS,HST,AST,HR,AR\n"
           "E0,01/01/2020,A,B,2,1,0,0,A,10,5,12,2,0,9\n").encode()
    df, _ = ingest.parse_season_zip(_zip(tmp_path, {"E0.csv": csv}), "1920")
    r = df.iloc[0]
    assert r.total_goals == 3 and r.over25 == 1.0
    assert r.flag_htr_inconsistent and r.flag_shots_target_gt_shots and r.flag_red_cards_gt_5


def test_division_outside_universe_is_reported_not_parsed(tmp_path):
    csv = "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG\nX9,01/01/2020,A,B,1,0\n".encode()
    df, rep = ingest.parse_season_zip(_zip(tmp_path, {"X9.csv": csv}), "1920")
    assert df.empty and rep[0]["status"] == "division_not_in_universe"

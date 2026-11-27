"""Fase Cero — verificación bibliográfica reproducible.

Para cada referencia candidata:
  1. Consulta Crossref por DOI -> título, autores, revista, año, volumen, páginas.
  2. Consulta OpenAlex por DOI -> resumen (si existe) y nº de citas.
Las referencias sin DOI se buscan por texto y se listan los candidatos para revisión manual.

Una referencia solo se cita en RESEARCH_FOUNDATIONS.md si su DOI resolvió y el título
coincide con lo esperado (revisión humana/LLM del JSON de salida).

No envía datos personales: User-Agent genérico, sin correo.
Uso: python phase0/verify_references.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "research" / "references_verified.json"
# Los resúmenes NO se versionan: OpenAlex no redistribuye resúmenes en texto plano por razones
# legales y los derechos pertenecen a las editoriales. Se guardan solo localmente (gitignored).
ABSTRACTS_LOCAL = ROOT / "research" / "abstracts_local.json"
UA = {"User-Agent": "quantitative-sports-research/0.1 (reference verification)"}

# Nota: 5 DOIs iniciales (escritos de memoria) resolvían a otros artículos o no existían;
# se corrigieron tras búsqueda bibliográfica en Crossref (ver EXPERIMENT_LOG.md, E-000).
DOIS = {
    # Modelos de goles / resultados
    "maher1982": "10.1111/j.1467-9574.1982.tb00782.x",
    "dixon_coles1997": "10.1111/1467-9876.00065",
    "rue_salvesen2000": "10.1111/1467-9884.00243",
    "karlis_ntzoufras2003": "10.1111/1467-9884.00366",
    "goddard2005": "10.1016/j.ijforecast.2004.08.002",
    "baio_blangiardo2010": "10.1080/02664760802684177",
    "koopman_lit2015": "10.1111/rssa.12042",
    "koopman_lit2019": "10.1016/j.ijforecast.2018.10.011",
    "boshnakov2017": "10.1016/j.ijforecast.2016.11.006",
    "egidi2018": "10.1177/1471082X18798414",
    "ley2019": "10.1177/1471082X18817650",
    "hvattum_arntzen2010": "10.1016/j.ijforecast.2009.10.002",
    "lasek2013": "10.1504/IJAPR.2013.052339",
    "mead2023_xg": "10.1371/journal.pone.0282295",
    "wheatcroft2020_ou": "10.1016/j.ijforecast.2019.11.001",
    "wheatcroft2021_stats": "10.3233/JSA-200462",
    "wheatcroft2021_rps": "10.1515/jqas-2019-0089",
    "constantinou_fenton2012": "10.1515/1559-0410.1418",
    "constantinou2013": "10.1016/j.knosys.2013.05.008",
    # ML aplicado
    "hubacek2019": "10.1016/j.ijforecast.2019.01.001",
    "walsh_joshi2024": "10.1016/j.mlwa.2024.100539",
    "bunker_susnjak2022": "10.1613/jair.1.13509",
    "horvat_job2020": "10.1002/widm.1380",
    # Mercados de apuestas
    "dixon_pope2004": "10.1016/j.ijforecast.2003.12.007",
    "forrest2005": "10.1016/j.ijforecast.2005.03.003",
    "kuypers2000": "10.1080/00036840050151449",
    "cain2000": "10.1111/1467-9485.00151",
    "levitt2004": "10.1111/j.1468-0297.2004.00207.x",
    "spann_skiera2009": "10.1002/for.1091",
    "angelini2019": "10.1016/j.ijforecast.2018.07.008",
    "wunderlich_memmert2018": "10.1371/journal.pone.0198668",
    "snowberg_wolfers2010": "10.1086/655844",
    "gandar1998_nba": "10.1111/0022-1082.155346",
    "manner2016_nba": "10.1515/jqas-2015-0088",
    "gandar2000_nba_totals": "10.1177/152700250000100205",
    "paul_weinbach2002_totals": "10.1177/1527002502003003003",
    "nba_player_absence2015": "10.1016/j.frl.2015.02.004",
    # Eliminación del margen
    "shin1991": "10.2307/2234434",
    "shin1993": "10.2307/2234240",
    "strumbelj2014": "10.1016/j.ijforecast.2014.02.008",
    "clarke2017": "10.11648/j.ajss.20170506.12",
    # Tarjetas / árbitros
    "dawson2007": "10.1111/j.1467-985x.2006.00451.x",
    "boyko2007": "10.1080/02640410601038576",
    # Evaluación probabilística / calibración
    "brier1950": "10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2",
    "murphy1973": "10.1175/1520-0450(1973)012<0595:ANVPOT>2.0.CO;2",
    "gneiting_raftery2007": "10.1198/016214506000001437",
    "cox1958": "10.1093/biomet/45.3-4.562",
    "zadrozny_elkan2002": "10.1145/775047.775151",
    "niculescu_caruana2005": "10.1145/1102351.1102430",
    "vancalster2019": "10.1186/s12916-019-1466-7",
    # Inferencia, backtesting, selección múltiple
    "diebold_mariano1995": "10.1080/07350015.1995.10524599",
    "kunsch1989": "10.1214/aos/1176347265",
    "politis_romano1994": "10.1080/01621459.1994.10476870",
    "white2000": "10.1111/1468-0262.00152",
    "hansen2005": "10.1198/073500105000000063",
    "benjamini_hochberg1995": "10.1111/j.2517-6161.1995.tb02031.x",
    "bailey2017_pbo": "10.21314/JCF.2016.322",
    "bailey_lopezdeprado2014_dsr": "10.3905/jpm.2014.40.5.094",
    "harvey_liu2015": "10.3905/jpm.2015.42.1.013",
}

SEARCH = {  # sin DOI conocido: buscar candidatos
    "paul_weinbach_nba_totals": "Paul Weinbach NBA totals betting market efficiency",
    "corners_count_model": "corner kicks football count model prediction betting",
    "nba_player_props_efficiency": "NBA player prop betting market efficiency",
    "cards_betting_market": "bookings cards football betting market referee prediction",
    "ou_goals_market_efficiency": "over/under goals betting market efficiency association football",
    "nba_totals_bias": "NBA totals over under betting market bias",
    "nba_player_points_props": "player points over under betting lines basketball",
}


def http(method: str, url: str, attempts: int = 6, **kw) -> requests.Response:
    """Petición con reintentos ante 429/5xx (respeta Retry-After; espera exponencial).
    Corrección tras la verificación de reproducibilidad (E-002): sin reintentos, un 429 de
    Crossref degradaba silenciosamente el resultado."""
    wait = 2.0
    for i in range(attempts):
        r = requests.request(method, url, headers=UA, timeout=60, **kw)
        if r.status_code not in (429, 500, 502, 503, 504) or i == attempts - 1:
            return r
        ra = r.headers.get("Retry-After")
        time.sleep(float(ra) if ra and ra.replace(".", "", 1).isdigit() else wait)
        wait = min(wait * 2, 60)
    return r


def openalex(doi: str) -> dict:
    r = http("GET", f"https://api.openalex.org/works/doi:{doi}")
    if r.status_code != 200:
        return {"openalex_status": r.status_code}
    j = r.json()
    inv = j.get("abstract_inverted_index") or {}
    abstract = None
    if inv:
        pos = {p: w for w, ps in inv.items() for p in ps}
        abstract = " ".join(pos[i] for i in sorted(pos))
    return {"openalex_status": 200, "cited_by_count": j.get("cited_by_count"),
            "open_access_url": (j.get("open_access") or {}).get("oa_url"), "_abstract": abstract}


def semantic_scholar_abstracts(dois: dict[str, str]) -> tuple[dict[str, str | None], int]:
    """Resúmenes (o TLDR) vía Semantic Scholar batch, para los DOIs sin resumen en OpenAlex
    (p. ej. Elsevier). Reproduce el paso usado en la Fase Cero."""
    keys = list(dois)
    r = http("POST", "https://api.semanticscholar.org/graph/v1/paper/batch",
             params={"fields": "title,year,abstract,tldr"}, json={"ids": ["DOI:" + dois[k] for k in keys]})
    out: dict[str, str | None] = {k: None for k in keys}
    if r.status_code != 200:
        return out, r.status_code
    if r.status_code == 200:
        for k, p in zip(keys, r.json()):
            p = p or {}
            out[k] = p.get("abstract") or (("TLDR: " + p["tldr"]["text"]) if (p.get("tldr") or {}).get("text") else None)
    return out, r.status_code


def crossref(doi: str) -> dict:
    r = http("GET", f"https://api.crossref.org/works/{requests.utils.quote(doi, safe='/')}")
    if r.status_code != 200:
        return {"crossref_status": r.status_code}
    m = r.json()["message"]
    year = None
    for k in ("published-print", "published-online", "issued"):
        if m.get(k, {}).get("date-parts"):
            year = m[k]["date-parts"][0][0]
            break
    return {
        "crossref_status": 200,
        "title": (m.get("title") or [None])[0],
        "authors": [f"{a.get('family','')}, {a.get('given','')}".strip(", ") for a in m.get("author", [])],
        "journal": (m.get("container-title") or [None])[0],
        "year": year, "volume": m.get("volume"), "issue": m.get("issue"), "pages": m.get("page"),
    }


def main() -> None:
    res = {"dois": {}, "searches": {}}
    abstracts: dict[str, dict] = {}
    for key, doi in DOIS.items():
        rec = {"doi": doi, **crossref(doi)}
        time.sleep(0.2)
        oa = openalex(doi)
        time.sleep(0.2)
        abstracts[key] = {"openalex": oa.pop("_abstract", None)}
        rec |= oa
        rec["abstract_available_openalex"] = bool(abstracts[key]["openalex"])
        res["dois"][key] = rec
        print(f"{key:30s} {rec.get('crossref_status')} {rec.get('year')} | {str(rec.get('title'))[:90]}")
    for key, q in SEARCH.items():
        r = http("GET", "https://api.crossref.org/works", params={"query.bibliographic": q, "rows": 5})
        items = r.json()["message"]["items"] if r.status_code == 200 else []
        res["searches"][key] = [{"doi": it.get("DOI"), "title": (it.get("title") or [None])[0],
                                 "journal": (it.get("container-title") or [None])[0],
                                 "year": (it.get("issued", {}).get("date-parts") or [[None]])[0][0],
                                 "authors": [a.get("family") for a in it.get("author", [])]}
                                for it in items]
        time.sleep(0.3)
    s2, s2_status = semantic_scholar_abstracts(DOIS)
    for key in DOIS:
        abstracts[key]["semanticscholar"] = s2.get(key)
        res["dois"][key]["abstract_available_semanticscholar"] = bool(s2.get(key))
    res["_note"] = ("Resúmenes no incluidos: OpenAlex no redistribuye resúmenes en texto plano por razones "
                    "legales y los derechos pertenecen a las editoriales. Regenerables localmente con "
                    "phase0/verify_references.py (salida en research/abstracts_local.json, ignorada por git).")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    failed = [k for k, v in res["dois"].items() if v.get("crossref_status") != 200]
    ABSTRACTS_LOCAL.write_text(json.dumps(abstracts, indent=1, ensure_ascii=False))
    if failed or s2_status != 200:
        partial = OUT.with_name("references_verified.partial.json")
        partial.write_text(json.dumps(res, indent=1, ensure_ascii=False))
        raise SystemExit(f"Verificación incompleta (Crossref fallidos: {failed}; Semantic Scholar HTTP {s2_status}). "
                         f"NO se sobrescribió {OUT.name}; salida parcial en {partial.name}. Reintente más tarde.")
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

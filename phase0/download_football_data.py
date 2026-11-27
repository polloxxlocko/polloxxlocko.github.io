"""Fase Cero — descarga RAW de Football-Data.co.uk (archivos data.zip por temporada).

Propósito: auditoría de factibilidad (cobertura de cuotas y estadísticas). No entrena modelos.

Reglas:
- Los archivos se guardan sin modificar (capa RAW).
- Cada descarga queda registrada en un manifiesto append-only (JSONL) con URL,
  fecha/hora UTC de recolección, tamaño y SHA-256.
- Si el archivo ya existe, NO se sobrescribe: se registra su hash actual y se omite.
- Pausa entre peticiones para no sobrecargar la fuente.

Uso:
    python phase0/download_football_data.py --first 0001 --last 2627
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import time
from pathlib import Path

import requests

BASE = "https://www.football-data.co.uk/mmz4281/{season}/data.zip"
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "football_data"
MANIFEST = RAW / "manifest.jsonl"
USER_AGENT = "quantitative-sports-research/0.1 (non-commercial research; polite crawler)"


def season_codes(first: str, last: str) -> list[str]:
    """'0001'..'2627' -> lista de códigos consecutivos (YYyy)."""
    a, b = int(first[:2]), int(last[:2])
    out = []
    for y in range(a, b + 1):
        out.append(f"{y:02d}{(y + 1) % 100:02d}")
    return out


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", default="0001")
    ap.add_argument("--last", default="2627")
    ap.add_argument("--sleep", type=float, default=2.0)
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    # GUARDA GATE 1 (2026-11-27): este script histórico escribe todo en data/raw/. Las temporadas
    # reservadas (>= 2024/25) deben descargarse con `python -m qsports download`, que las
    # enruta a su partición sellada. Se niega a procesar temporadas reservadas.
    reserved = [c for c in season_codes(args.first, args.last) if c >= "2425"]
    if reserved:
        raise SystemExit(f"Temporadas reservadas {reserved}: use 'python -m qsports download'.")
    for code in season_codes(args.first, args.last):
        dest = RAW / code / "data.zip"
        url = BASE.format(season=code)
        rec = {"source": "football-data.co.uk", "season_code": code, "url": url}
        if dest.exists():
            rec |= {"status": "exists_skipped", "bytes": dest.stat().st_size, "sha256": sha256(dest),
                    "checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
        else:
            r = s.get(url, timeout=120, allow_redirects=True)
            rec |= {"http_status": r.status_code, "final_url": r.url,
                    "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "last_modified_header": r.headers.get("Last-Modified")}
            if r.status_code == 200 and r.content[:2] == b"PK":
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_suffix(".part")
                tmp.write_bytes(r.content)
                tmp.rename(dest)
                rec |= {"status": "downloaded", "bytes": dest.stat().st_size, "sha256": sha256(dest)}
            else:
                rec |= {"status": "failed", "content_prefix": r.content[:40].hex()}
            time.sleep(args.sleep)
        with MANIFEST.open("a") as m:
            m.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(code, rec["status"], rec.get("bytes"))


if __name__ == "__main__":
    main()

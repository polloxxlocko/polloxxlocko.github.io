"""CLI: python -m qsports <download|build|verify|reports>"""
from __future__ import annotations

import argparse
import json


def main() -> None:
    ap = argparse.ArgumentParser(prog="qsports")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("download", help="Descarga RAW enrutada por partición (no sobrescribe)")
    d.add_argument("--first", default="0001")
    d.add_argument("--last", default="2627")
    b = sub.add_parser("build", help="Sella reservados, construye dev, benchmarks y manifiesto")
    b.add_argument("--download", action="store_true")
    sub.add_parser("verify", help="Verifica hashes e invariantes de protección")
    sub.add_parser("reports", help="Genera inventario, calidad y diagnósticos temporales (GATE 1)")
    sub.add_parser("audit-synthetic", help="Pipeline completo en datos sintéticos (sin datos de la fuente ni sellados)")
    sub.add_parser("audit-package", help="Paquete de auditoría reproducible (git archive verificado)")
    a = ap.parse_args()
    if a.cmd == "download":
        from .ingest import download_seasons, season_codes
        for r in download_seasons(season_codes(a.first, a.last)):
            print(r["season_code"], r["partition"], r["status"])
    elif a.cmd == "build":
        from .process import build
        print(json.dumps(build(download=a.download), indent=1, default=str)[:4000])
    elif a.cmd == "verify":
        from .verify import verify_all
        res = verify_all()
        print(json.dumps(res, indent=1, default=str))
        raise SystemExit(0 if res["ok"] else 1)
    elif a.cmd == "audit-package":
        from .audit_package import build
        build()
    elif a.cmd == "audit-synthetic":
        from .audit_synthetic import main as audit_main
        raise SystemExit(0 if audit_main()["ok"] else 1)
    elif a.cmd == "reports":
        from .quality import generate_all
        print(json.dumps(generate_all(), indent=1, default=str)[:4000])


if __name__ == "__main__":
    main()

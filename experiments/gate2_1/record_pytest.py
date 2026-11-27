"""Registro de pruebas ligado a un commit exacto (GATE 2.1, exigencia 6).

Uso: python experiments/gate2_1/record_pytest.py
Exige un árbol de trabajo limpio. Ejecuta `python -m pytest -v` sobre el commit actual y escribe:
  reports/gate2_1/pytest_<commit7>.txt   salida completa, con cabecera (commit, árbol limpio, entorno, comando)
  reports/gate2_1/pytest_<commit7>.xml   JUnit XML
  reports/gate2_1/pytest_<commit7>.json  resumen (conteos por resultado, duración, ejecutor)
El registro documenta una ejecución hecha por Claude en su contenedor, no comprobaciones del auditor.
"""
import datetime as dt
import json
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "gate2_1"


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def main():
    if git("status", "--porcelain"):
        sys.exit("Árbol con cambios sin commit: el registro debe corresponder a un commit exacto.")
    commit = git("rev-parse", "HEAD")
    c7 = commit[:7]
    OUT.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "pytest", "-v", "-p", "no:cacheprovider", f"--junitxml={OUT / f'pytest_{c7}.xml'}"]
    t0 = dt.datetime.now(dt.timezone.utc)
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    t1 = dt.datetime.now(dt.timezone.utc)
    head = {"commit": commit, "tree_clean_at_start": True, "executed_by": "Claude (agente), contenedor cloud del proyecto",
            "command": "python -m pytest -v -p no:cacheprovider --junitxml=...", "started_utc": t0.isoformat(),
            "finished_utc": t1.isoformat(), "python": sys.version.split()[0], "platform": platform.platform(),
            "exit_code": r.returncode}
    suite = ET.parse(OUT / f"pytest_{c7}.xml").getroot()
    suite = suite if suite.tag == "testsuite" else suite.find("testsuite")
    counts = {k: int(suite.get(k, 0)) for k in ("tests", "failures", "errors", "skipped")}
    counts["passed"] = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
    head["counts"] = counts
    other = [x for x in git("status", "--porcelain").splitlines() if f"pytest_{c7}." not in x and "reports/gate2_1/" not in x]
    head["tree_clean_at_end_excluding_this_record"] = not other
    (OUT / f"pytest_{c7}.txt").write_text("# " + json.dumps(head, ensure_ascii=False) + "\n" + r.stdout + r.stderr)
    (OUT / f"pytest_{c7}.json").write_text(json.dumps(head, indent=1, ensure_ascii=False))
    print(json.dumps(head, indent=1, ensure_ascii=False))
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()

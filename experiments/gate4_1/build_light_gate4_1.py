"""ZIP ligero de GATE 4.1 (como el de GATE 4: + GATE3_AUTHORIZATION.json y PROTOCOL_FREEZE.json).
Uso: python experiments/gate4_1/build_light_gate4_1.py -> dist/audit_package_gate4_1_light.zip"""
from qsports import audit_package as ap

ap.LIGHT_TOP_FILES = ap.LIGHT_TOP_FILES + ("GATE3_AUTHORIZATION.json", "PROTOCOL_FREEZE.json")
ap.build_light("audit_package_gate4_1_light.zip")

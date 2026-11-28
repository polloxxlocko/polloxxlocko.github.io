"""ZIP ligero de GATE 4: `audit-package --light` + GATE3_AUTHORIZATION.json + PROTOCOL_FREEZE.json (necesarios para
verificar el registro de la valla y el hash del protocolo congelado). Sin modificar el código congelado.
Uso: python experiments/gate4/build_light_gate4.py -> dist/audit_package_gate4_light.zip"""
from qsports import audit_package as ap

ap.LIGHT_TOP_FILES = ap.LIGHT_TOP_FILES + ("GATE3_AUTHORIZATION.json", "PROTOCOL_FREEZE.json")
ap.build_light("audit_package_gate4_light.zip")

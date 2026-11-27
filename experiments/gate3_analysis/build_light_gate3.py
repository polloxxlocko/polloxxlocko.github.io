"""ZIP ligero de GATE 3: el de `audit-package --light` más GATE3_AUTHORIZATION.json, necesario para que el registro de
la valla (con cruces autorizados) sea verificable. Se hace aquí, sin modificar el código congelado.
Uso: python experiments/gate3_analysis/build_light_gate3.py -> dist/audit_package_gate3_light.zip"""
from qsports import audit_package as ap

ap.LIGHT_TOP_FILES = ap.LIGHT_TOP_FILES + ("GATE3_AUTHORIZATION.json",)
ap.build_light("audit_package_gate3_light.zip")

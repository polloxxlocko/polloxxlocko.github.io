"""ZIP ligero final: `audit-package --light` + GATE3_AUTHORIZATION.json, HOLDOUT_AUTHORIZATION.json y
PROTOCOL_FREEZE.json (necesarios para verificar los registros de la valla, del holdout y el hash del protocolo).
Está fuera de experiments/final/ para no alterar el hash del código congelado.
Uso: python experiments/final_records/build_light_final.py -> dist/audit_package_final_light.zip"""
from qsports import audit_package as ap

ap.LIGHT_TOP_FILES = ap.LIGHT_TOP_FILES + ("GATE3_AUTHORIZATION.json", "HOLDOUT_AUTHORIZATION.json", "PROTOCOL_FREEZE.json")
ap.build_light("audit_package_final_light.zip")

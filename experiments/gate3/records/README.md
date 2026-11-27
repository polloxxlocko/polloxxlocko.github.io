# Registros de GATE 3 (ejecutados por Claude)

- `pytest_2e04fca.*`: **3 fallos**. Tres pruebas de la valla suponían que no existía autorización de GATE 3,
  pero la autorización real ya existía. El fallo no estaba en el código, sino en la dependencia de las
  pruebas respecto del estado del proyecto. Se conserva como evidencia. El registro de la valla no se
  alteró: las pruebas escriben en uno temporal.
- Corrección: las tres pruebas usan una raíz temporal sin autorización y son herméticas. El registro
  válido es el del commit siguiente (`pytest_<commit>.*`, ver `TEST_RECORD_GATE3.md`).
- `HASH_MANIFEST_GATE3.json`: hashes de código, candidatos congelados, autorización, sello, registro de
  la valla, dataset, ejecución de validación, reproducción de referencia y documentos.

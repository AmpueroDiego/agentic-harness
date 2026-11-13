---
tipo: evaluacion
fecha: 2026-11-13
tags: [harness, evaluacion, golden-tasks]
---

# Tareas doradas para replay

Este conjunto anonimizado permite repetir cuatro escenarios de instalación, guardas y orquestación. Las tareas están en `golden-tasks.json`; la salida del runner entrega el prompt y las verificaciones esperadas. No invoca un modelo ni reporta resultados por sí sola.

## Repetición

```sh
python scripts/replay_golden_tasks.py
python scripts/replay_golden_tasks.py --id GT-03
```

Corre cada prompt contra una rama limpia del commit evaluado. Registra modelo/versión, commit, fecha, resultado de cada check, tokens y duración en el reporte de evaluación. Haz tres repeticiones por tarea para distinguir regresiones de variación del modelo. El CI valida el harness y las fixtures; no sustituye la ejecución de agentes.

La cifra histórica de 175 tareas no incluye en esta versión pública un dataset de resultados, denominador de éxito ni mediciones comparables. No debe presentarse como tasa de éxito, regresiones evitadas o ahorro.

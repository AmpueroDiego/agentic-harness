---
name: diagnosing-bugs
description: Diagnostica fallos difíciles o intermitentes en un proyecto de Llama Solutions cuando la causa no está clara. Busca una señal reproducible antes de proponer la corrección.
---

# Diagnosticar un fallo

Lee las instrucciones y el contrato del proyecto dueño. Delimita el comportamiento esperado, el observado, el entorno y la última evidencia confiable. Redacta secretos y datos personales al registrar ejemplos.

Busca la señal de fallo más pequeña y determinista disponible: un caso ya documentado, salida HTTP o CLI, logs acotados, una navegación de Playwright, o una traza. Elige la herramienta que corresponda al síntoma; no conviertas cada diagnóstico en un recorrido completo. No añadas ni ejecutes pruebas salvo que el usuario lo solicite o las instrucciones del proyecto lo exijan.

Con la señal definida, traza el camino real del código y plantea hipótesis que puedan refutarse. Cambia una variable por vez cuando sea práctico. Distingue hechos observados, inferencias y dudas. Si la reproducción requiere credenciales, datos de producción o una acción externa, aplica las reglas de permisos del Harness antes de continuar.

Entrega la causa respaldada por evidencia o el conjunto acotado de hipótesis restantes, las rutas y símbolos relevantes, el cambio propuesto y qué comprobación confirmaría la solución. Si el usuario pidió corregir el fallo, continúa con el flujo de implementación del proyecto.

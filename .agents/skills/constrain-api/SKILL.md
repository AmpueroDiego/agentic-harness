---
name: constrain-api
description: Acota una API, SDK o dependencia a los usos permitidos por un proyecto de Llama Solutions. Úsala cuando el usuario pida limitar imports, métodos, propiedades o dependencias entre módulos con reglas verificables.
---

# Acotar una API

Lee las instrucciones, manifiestos y reglas de lint del proyecto dueño. Identifica una sola API o frontera para este trabajo y cómo se usa hoy. Distingue imports, propiedades, métodos y dependencias entre módulos. Consulta la documentación oficial del proveedor cuando una restricción dependa de su contrato.

Propón una superficie permitida pequeña, con rutas y usos observados. Para cada uso que quedaría fuera, indica una alternativa concreta. Si ya existen infracciones, separa las nuevas de las heredadas y plantea una reducción gradual sin ocultarlas.

Si el usuario pidió implementar la restricción, usa el analizador o linter existente del proyecto cuando pueda expresarla. Mantén la regla junto al código que gobierna. No conviertas una preferencia de estilo en un bloqueo global ni añadas dependencias de análisis sin justificar la necesidad.

Entrega la frontera acordada, el mecanismo que la comprueba, los archivos afectados y las limitaciones de detección. Indica qué comprobaciones se ejecutaron realmente. Aplica los permisos y el flujo de revisión del Harness; esta skill no autoriza cambios de seguridad ni pruebas no solicitadas.

# Run: presentación de capacidades del Harness

## Objetivo y condición de cierre

- Objetivo: explicar las capacidades reales en el README principal con mayor detalle y ejemplos útiles.
- Cierre: cubrir grounding, agentes, skills, scripts, español sencillo, MCP, Obsidian, ADRs, runs y retrospectivas.
- Criterio adicional: presentar Funnel Studio como módulo opcional y atribuir el material de terceros.
- Riesgo: bajo; cambio documental reversible y local, sin publicación ni cambios del runtime.

## Decisiones y acciones revisadas

| Acción | Destino | Autorización o revisión | Resultado | Motivo |
|---|---|---|---|---|
| Reescribir presentación | `README.md` | Pedido del usuario; escritura dentro del workspace | Hecho | Mostrar capacidades y casos de uso con fuentes. |
| Inventariar fuentes | Perfiles, skills, scripts y memoria | Lecturas locales y exploradores acotados | Hecho | Distinguir código portable, adaptadores y dependencias externas. |
| Documentar comandos MCP | Sección MCP | Documentación oficial consultada | Hecho | Explicar conexión sin crear servidores ni guardar credenciales. |

## Cambios y evidencia

- Archivos de esta ampliación: `README.md`, este registro e índice de memoria.
- Se conservaron cambios previos en `.codex/browser/README.md` y `LLAMA-HARNESS.md`.
- Plan: perfil `planner`, con aceptación y revisión de contenido definidas.
- Inventario comprobado por el principal: 37 archivos `SKILL.md`, 34 con marca de generación y tres manuales.
- Entradas manuales: `ux-review`, `llama-funnel-studio` y `security`; esta última conserva contexto heredado.
- Atribuciones contrastadas con NOTICE y licencias incluidas; no se auditó compatibilidad jurídica.
- Fuente MCP: https://learn.chatgpt.com/docs/extend/mcp?surface=cli, consultada el 2026-11-16.
- Comprobaciones: 73 enlaces del README examinados; los destinos locales existen.
- `git diff --check`: sin errores de formato; Git avisa de conversión futura de LF a CRLF.
- Revisión de extensión de oraciones: sin frases de prosa superiores a 20 palabras según el conteo local.
- Pruebas de código y scripts: no ejecutadas; la modificación es documental.
- QA: `qa_reviewer` devolvió PASS sobre el contenido y la evidencia suministrada por el principal.
- Límite de QA: el revisor no inspeccionó archivos mediante herramientas; el principal comprobó inventario y enlaces directamente.

## Resultado

- Estado: completo; el README cubre todos los temas pedidos y distingue capacidades, compatibilidad y dependencias.
- Pendientes: ninguno para la edición documental; no se validó el funcionamiento de todas las skills o integraciones.
- Publicación: cambios locales; no se hizo commit, push ni pull request durante esta tarea.

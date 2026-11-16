---
tipo: indice
tags: [harness, codex, onboarding]
---

# Llama Agentic Harness

Versión propuesta: **2.0.0**. Consulta [VERSION](VERSION).

Sistema de trabajo para Codex con agentes especializados, revisiones, controles y memoria en Markdown.

El agente principal dirige el trabajo y comprueba los resultados.
Cada proyecto conserva sus instrucciones, código y decisiones.

## Empezar

1. Clona este repositorio.
2. Abre su carpeta raíz en Codex.
3. Lee [AGENTS.md](AGENTS.md) y [LLAMA-HARNESS.md](LLAMA-HARNESS.md).
4. Revisa los modelos de `.codex/agents/` según tu acceso.
5. Revisa y confía los hooks mediante `/hooks`, si tu versión admite esa función.
6. Mantén las credenciales y los proyectos de aplicación fuera del repositorio.

La configuración del proyecto habilita agentes y limita su concurrencia.
La configuración global de permisos sigue bajo control del usuario.
Este repositorio no concede permisos ni configura automáticamente integraciones externas.

## Componentes

| Ruta | Contenido |
|---|---|
| [AGENTS.md](AGENTS.md) | Reglas de trabajo y coordinación |
| [.codex/README.md](.codex/README.md) | Configuración, agentes y hooks de Codex |
| [.agents/skills/](.agents/skills/) | Skills nativas y adaptadores del Harness existente |
| [CodexMemory/INDEX.md](CodexMemory/INDEX.md) | Flujo de trabajo, decisiones y registros |
| [Funnel Studio](systems/llama-funnel-studio/README.md) | Protocolos y herramientas para analizar y adaptar funnels |
| [.codex/templates/run-record.md](.codex/templates/run-record.md) | Plantilla de evidencia para trabajos importantes |
| [MCP y REPL](docs/mcp-repl.md) | Descubrimiento diferido y ejecución persistente |
| [Auditoría](docs/harness-audit.md) | Decisiones, límites y componentes conservados |

El Harness incluye nueve perfiles de agentes.
Funnel Studio aporta 24 funciones de dominio.
El agente principal activa únicamente los especialistas necesarios.

## Uso diario

- Resuelve cambios pequeños directamente.
- Planifica cambios relevantes antes de implementarlos.
- Delega tareas independientes con archivos asignados.
- Revisa los cambios de seguridad, datos y contratos mediante agentes independientes.
- Limita cada ciclo de reparación a dos rondas.
- Registra decisiones importantes y comprobaciones reales.

Usa `$ux-review` para revisar una interfaz.
Usa `$llama-funnel-studio` para analizar o adaptar un funnel.

## Herramientas opcionales

Node.js ejecuta los hooks incluidos.
Python ejecuta los analizadores de Funnel Studio.
Playwright permite capturar páginas con un navegador instalado y un perfil temporal.

Consulta las dependencias en [tools/README.md](systems/llama-funnel-studio/tools/README.md).
La documentación del navegador está en [.codex/browser/README.md](.codex/browser/README.md).

## Compatibilidad con Claude

El repositorio conserva `.claude/`, los perfiles anteriores y las skills de diseño.
La documentación anterior sigue en [README.claude.md](README.claude.md).
Las instrucciones específicas de Claude siguen en [CLAUDE.md](CLAUDE.md).
Los adaptadores generados conservan su fuente en `.claude/`.

El instalador existente configura el Harness de Claude.
No lo necesitas para abrir este repositorio con Codex.
Consulta [AGENTS.claude.md](AGENTS.claude.md) para las equivalencias del flujo anterior.

## Publicación y seguridad

Publica cambios mediante una rama y un pull request.
Conserva la licencia y el historial existente.
Revisa el contenido preparado antes de cada publicación.

Los hooks complementan los permisos del entorno.
Los agentes revisores no crean un aislamiento de seguridad.
Los ejemplos de configuración no incluyen credenciales.

Consulta el [registro de publicación](CodexMemory/runs/2026-11-16-publicar-harness.md).

Licencia: [MIT](LICENSE).

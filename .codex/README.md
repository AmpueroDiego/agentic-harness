# Configuración de Codex

Abre la raíz del repositorio para descubrir los agentes y las skills locales.
Revisa [AGENTS.md](../AGENTS.md) antes de trabajar.

## Agentes

Los perfiles están en `agents/`.
El archivo `config.toml` habilita agentes y limita la concurrencia.
Cada perfil declara su función y sus límites.
`architecture_reviewer` propone mejoras de arquitectura con evidencia y no modifica código.
Algunos perfiles seleccionan modelos concretos.
Adapta esa selección a los modelos disponibles en tu cuenta.

El agente principal asigna el alcance y comprueba la evidencia.
Los revisores devuelven `PASS` o `FINDINGS`.
Los agentes heredan el sandbox del proceso principal.
Una instrucción de solo lectura no constituye aislamiento.

## Permisos y hooks

Configura los permisos globales de Codex desde tu instalación.
El perfil recomendado combina `workspace-write` y aprobaciones `on-request`.
Usa Auto-review únicamente cuando tu instalación lo admita.
El repositorio no cambia esos permisos globales.

`hooks.json` referencia `hooks/pre_tool_use_guard.cjs` desde la raíz del repositorio.
Node.js debe estar disponible en el `PATH`.
Revisa y confía la definición exacta mediante `/hooks` antes de utilizarla.
El matcher incluido cubre la herramienta `Bash`.
No afirma cubrir PowerShell ni todas las herramientas del entorno.

El guard detecta algunos comandos destructivos y patrones frecuentes de secretos.
Sus patrones pueden producir falsos positivos o dejar casos sin detectar.
Consulta los [escenarios de control](../CodexMemory/guardrail-scenarios.md).

## Flujo y memoria

Consulta el [flujo por riesgo](../CodexMemory/workflow.md).
Usa [run-record.md](templates/run-record.md) para registrar trabajos importantes.
Guarda las decisiones de cada aplicación junto a su proyecto.
Mantén los registros privados fuera de este repositorio público.

## Sistemas opcionales

[Funnel Studio](../systems/llama-funnel-studio/README.md) incluye protocolos y herramientas de dominio.
La skill `$llama-funnel-studio` conecta esos protocolos con Codex.
La skill `$ux-review` permite revisar interfaces con evidencia real.
Las skills `$align-to-spec` y `$diagnosing-bugs` cubren requisitos ambiguos y fallos difíciles.
La skill `$constrain-api` ayuda a expresar límites verificables sobre un SDK o una dependencia del proyecto.

El Harness conserva las herramientas anteriores de Claude en `.claude/`.
Sus adaptadores no sustituyen los perfiles nativos de Codex.

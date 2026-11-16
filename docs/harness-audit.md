---
tipo: auditoria
fecha: 2026-11-16
tags: [harness, codex, publicacion, compatibilidad]
---

# Auditoría de Llama Agentic Harness 2.0.0

Esta auditoría documenta las decisiones de integración de la versión propuesta.
El registro de publicación debe conservar los resultados finales de validación y revisión.
Consulta el [README](../README.md) y la [arquitectura](../LLAMA-HARNESS.md).

## Alcance

La propuesta incorpora el Harness nativo de Codex al repositorio `agentic-harness`.
Conserva la implementación anterior de Claude y sus componentes reutilizables.
La comparación cubre arquitectura, instrucciones, herramientas, memoria y límites de publicación.
La auditoría no certifica todos los clientes, modelos o servicios externos.

## Qué conservamos

| Componente | Decisión | Motivo |
|---|---|---|
| `.claude/` | Conservar | Mantiene los comandos, agentes y controles anteriores |
| Skills de diseño | Conservar | Aportan protocolos reutilizables para interfaces y contenido |
| Adaptadores generados | Conservar | Mantienen su fuente en `.claude/` |
| `profiles/` | Conservar | Documenta convenciones de diferentes stacks |
| Licencia e historial | Conservar | Mantiene atribución y trazabilidad |
| Documentación anterior | Conservar con nombres explícitos | Permite consultar el flujo anterior sin confundirlo con Codex |

La documentación anterior permanece en [README.claude.md](../README.claude.md) y [AGENTS.claude.md](../AGENTS.claude.md).
[CLAUDE.md](../CLAUDE.md) conserva las reglas específicas de ese flujo.

## Qué incorporamos

| Componente | Aporte | Límite |
|---|---|---|
| `.codex/agents/` | Nueve perfiles con funciones delimitadas | Los modelos dependen de la cuenta |
| `.codex/config.toml` | Configuración local de agentes | El cliente debe admitir sus campos |
| `.codex/hooks/` | Controles revisables | Los patrones no cubren todos los riesgos |
| `.codex/templates/` | Formato de evidencia | El agente debe registrar comprobaciones reales |
| `CodexMemory/` | Flujo y memoria compartida | Excluye información privada de aplicaciones |
| Funnel Studio | Protocolos y herramientas de dominio | Activa solo las disciplinas necesarias |
| Skills nativas | Entradas para UX y funnels | Cada proyecto conserva sus instrucciones |

Los especialistas de Funnel Studio siguen sus contratos de entrada y salida.
El agente principal conserva la coordinación y las decisiones de alcance.

## Qué adaptamos

La propuesta coloca Funnel Studio en `systems/llama-funnel-studio/`.
Las referencias internas deben resolver desde esa ubicación.
Los comandos de hooks utilizan rutas relativas al repositorio.
La documentación del navegador describe un entorno instalable sin rutas personales.
La portada presenta Codex y enlaza explícitamente el flujo anterior.

Los adaptadores generados siguen apuntando a sus fuentes originales.
Las skills nativas no deben modificar esas fuentes accidentalmente.
El equipo debe comprobar los enlaces y los adaptadores antes de publicar.

## Qué excluimos

- Archivos `.env` y otras credenciales.
- Bases de datos, certificados y claves privadas.
- Casos de clientes y materiales de aplicaciones.
- Registros privados del workspace original.
- Cookies, perfiles y sesiones del navegador.
- Binarios descargados, cachés y dependencias instaladas.
- Configuración global de permisos y conexiones personales.

La preparación utiliza una lista explícita de archivos reutilizables.
El equipo debe revisar el contenido preparado y el diff antes del push.
Una regla de `.gitignore` no sustituye esa revisión.

## MCP diferido y REPL

La [guía de MCP y REPL](mcp-repl.md) separa capacidades alojadas y archivos del repositorio.
El entorno descubre herramientas mediante los mecanismos que realmente ofrece.
El Harness no fabrica una herramienta ausente ni crea un servidor MCP automáticamente.

El REPL de Node conserva variables entre llamadas.
`functions.exec` crea un contexto JavaScript nuevo en cada llamada.
El REPL de computadora mantiene un contexto separado.
Cada entorno conserva sus propios permisos y restricciones.

## Límites confirmados

### Hooks

El matcher actual de [.codex/hooks.json](../.codex/hooks.json) cubre `Bash`.
No cubre automáticamente PowerShell, herramientas MCP ni todos los clientes.
El usuario debe revisar y confiar la definición antes de utilizarla.
Node.js debe resolver el comando desde el directorio esperado.
Los hooks complementan el sandbox y las aprobaciones.

### Revisores

Los perfiles revisores siguen instrucciones de revisión independiente.
Sus instrucciones no crean una frontera de seguridad.
Para garantizar solo lectura, utiliza permisos y herramientas que impidan escribir.
El agente principal debe comprobar los hallazgos y las pruebas declaradas.

### Compatibilidad

Los campos de configuración y los modelos pueden variar entre clientes.
El operador debe revisar su disponibilidad antes de activar un perfil.
El repositorio no instala servicios ni concede acceso a producción.
Cada integración externa requiere su propia configuración y autorización.

### Rendimiento

Las tareas independientes pueden trabajar en paralelo.
La delegación también añade coordinación, contexto y tiempo de revisión.
Los cambios pequeños deben conservar un flujo directo.
La caché y el REPL pueden reducir trabajo repetido.
La auditoría no promete respuestas instantáneas ni ahorros medidos.

## Comprobaciones de publicación

El responsable debe registrar los resultados concretos en el registro de publicación.

| Comprobación | Evidencia esperada |
|---|---|
| Contenido seleccionado | Lista de archivos y diff completo |
| Secretos | Resultado del escaneo y revisión del contenido preparado |
| Rutas portables | Ausencia de rutas personales en los archivos nuevos |
| Contratos | Archivos de agentes y skills legibles y válidos |
| Compatibilidad anterior | Validaciones existentes de skills y documentación |
| Hooks | Comprobaciones aplicables y límites de cobertura |
| Publicación | Rama, commit y pull request verificables |

Esta tabla define evidencia pendiente o requerida.
No afirma que todas las comprobaciones ya terminaron.

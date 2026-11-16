---
tipo: run
fecha: 2026-11-16
tags: [harness, codex, publicacion, auditoria]
---

# Publicar Llama Agentic Harness 2.0.0

## Objetivo y condición de cierre

- Publicar el Harness de Llama en `AmpueroDiego/agentic-harness` mediante una rama y un pull request.
- Mantener el sistema anterior de Claude y su licencia.
- Documentar el descubrimiento MCP diferido y el REPL con límites comprobables.
- Excluir credenciales, aplicaciones, casos privados y configuración personal.
- Riesgo alto: publicación externa de herramientas e instrucciones de seguridad.

## Decisiones y acciones

| Acción | Destino | Autorización y revisión | Resultado |
|---|---|---|---|
| Clonar e integrar | Repositorio indicado | Solicitud explícita del usuario | Copia aislada y rama de trabajo |
| Seleccionar fuentes | Archivos reutilizables del workspace | Inventario independiente | Lista explícita, sin copiar carpetas completas |
| Mantener compatibilidad | Instaladores y skills existentes | Plan y revisión independiente | Claude conserva sus instrucciones anteriores |
| Documentar herramientas | Guía MCP y REPL | Fuentes oficiales y observaciones del entorno | Capacidades externas claramente diferenciadas |
| Publicar | Rama `feature/llama-codex-harness` | Solicitud explícita; revisión previa | Pendiente de subida |

## Cambios y evidencia

- Nueve perfiles nativos de Codex y dos skills nativas.
- Hooks portables, plantilla de evidencia y configuración local de agentes.
- Protocolos reutilizables de Funnel Studio en `systems/llama-funnel-studio/`.
- Historial de mejoras vacío y sin datos de casos originales.
- README y AGENTS anteriores conservados para Claude.
- Instaladores anteriores adaptados a `AGENTS.claude.md`.
- `VERSION` declara `2.0.0`; esta publicación propone la versión, sin crear una release.
- REPL: dos llamadas confirmaron persistencia de estado.
- Validador del paquete: perfiles, skills, sintaxis Python y límites de exportación aprobados.
- Generador existente: 34 adaptadores vigentes y cero desactualizados.
- Pruebas del guard: cinco aprobadas después del ajuste de la fixture sintética.
- Instalador Windows: una prueba de integración aprobada.
- Validador documental: aprobado; conserva advertencias anteriores del vault y cinco perfiles huérfanos sin modificar.
- Las notas nuevas tienen enlaces desde sus índices.
- Seis comprobaciones anteriores de CI pasaron, incluidas 23 pruebas del detector de secretos.
- Revisión de privacidad: PASS después de corregir la fixture sintética.
- Revisión del sistema: PASS después de corregir codificación, enlaces y formatos de entrega.
- Revisión de contrato: PASS sobre la evidencia de compatibilidad y límites de publicación.
- El detector del guard inspeccionó el contenido preparado sin bloquear la publicación.

## Resultado

- Estado: en curso.
- El branch y el pull request quedarán como evidencia final.
- Los servidores MCP y las conexiones personales requieren configuración independiente.
- La cobertura del hook se limita al matcher Bash declarado.
- Los modelos y campos de configuración dependen del cliente y de la cuenta.

Consulta la [auditoría](../../docs/harness-audit.md) y el [índice de memoria](../INDEX.md).

---
tipo: guia-oficial
fecha: 2026-09-09
fuente: "Reconstruida el 2026-09-09 a partir de las filas de TASKS.md (2026-08-22 a 2026-08-26) y de la memoria del agente sobre el commit 4878e44. La nota original nunca llegó a escribirse — ver 'Sobre esta nota' al final."
tags: [retro, web-app, vista-agregada, agent-console, codex, leccion-aprendida]
aliases:
  - Retro Vista agregada Codex
  - retro-vista-agregada-agent-console
---

# 🔁 Retro — Vista agregada y Agent Console en `web-app`

> Referencia histórica anonimizada: los hallazgos, rutas y estados describen el sistema fuente en la fecha indicada. No afirman que los repos de ejemplo existan en este checkout ni que sus incidencias sigan vigentes.


> 🏠 **Navegación:** [[Home|Home (Dashboard)]] · [[TASKS|TASKS (Registro Vivo)]] · [[docs/guias/PLAYBOOK-ANTI-REGRESIONES-Y-LECCIONES-APRENDIDAS|Playbook Anti-Regresiones]] · [[contexto-negocio/web-app-arquitectura-frontend|Arquitectura Frontend web-app]] · [[contexto-negocio/web-app-relacion-api-core|Relacion web-app ↔ api-core]] · [[sistema-multiagente-supervisado|Sistema Multiagente Supervisado]]

---

## La lección, en una línea

**Antes de portar una rama larga, verificar si lo que trae ya existe en `develop` bajo otro nombre.** Vista agregada y `agent-console` habían crecido como dos linajes separados que resolvían casi lo mismo; el port se convirtió en una extensión del que ya estaba mergeado.

---

## 1. Qué pasó

El 2026-08-24 la tarea era portar `feature/vista-agregada-integracion` a `develop`. Al abrir la rama de trabajo (`feature/portar-vista-agregada-a-develop`) se descubrió que **`agent-console` — un linaje distinto, ya mergeado en `develop` — cubría casi toda la funcionalidad**.

La decisión fue **extender `agent-console` en vez de duplicar** la vista. La rama se pusheó sin PR y siguió siendo la base de trabajo del frontend durante los días siguientes:

| Fecha | Qué entró en esa rama | Commit |
|---|---|---|
| 2026-08-25 | Migración completa a Core Theme tokens + rediseño de Login split-screen | `8ed9813` |
| 2026-08-25 | Gestión de plantillas unificada en la Consola (`?view=templates`), retiro de `/plantillas` | `86b0f69` |

> [!info] Contexto previo
> Dos días antes (2026-08-22) ya se había renombrado la pestaña "Vista agregada" a **"Historial"** y se le habían agregado eventos de sistema. El nombre "Vista agregada" siguió usándose para el **endpoint del backend** (`ObtenerResumenPorIdentificador` en `api-core`), no para la pantalla — una fuente de confusión que conviene tener presente al leer TASKS o los ADRs.
>
> Y un día antes (2026-08-23), al recorrer el Core en vivo, se confirmó que la búsqueda de cliente y Vista agregada en `web-app` **seguían en modo mock**. El mock y la API real divergieron, y eso explica varios de los hallazgos de la sección siguiente.

---

## 2. Las rondas de revisión de Codex

Sobre `feature/mensajeria-realtime-registros-vista-agregada` cayeron cuatro rondas de observaciones automáticas en dos días:

| Fecha | Repo | Observaciones | Commit |
|---|---|---|---|
| 2026-08-26 | `api-core` | 11 — SignalR CORS, fail-safe realtime, tamaños, locks y mappings | `6492ba7` |
| 2026-08-26 | `web-app` | 9 — multirelacion, mock fallback, realtime read, templates y JWT | `9ef2d57` |
| 2026-08-26 | `api-core` | 5 — PROVEEDOR_MENSAJERIA credenciales, resolución de persona anticipada, `IdExterno` 450, DTO resumen SignalR, normalización sync | `d1f3d44` |
| 2026-08-26 | `web-app` | 11 (segunda ronda) — registros sintéticos, identificador reopen, cache snapshot, notes ownership, quality rating, catalogs | `75eeea2`, `5dc090d` |

Varias de esas observaciones se convirtieron después en reglas permanentes: la agregación multirelacion con `.reduce()`/`Math.max()` en vez de `relaciones[0]`, la decodificación de JWT base64url, el aislamiento de sesión en la SPA y `nvarchar(450)` para ids de proveedores externos. Todas viven hoy en [[docs/guias/PLAYBOOK-ANTI-REGRESIONES-Y-LECCIONES-APRENDIDAS|el Playbook]] y en `CLAUDE.md`.

---

## 3. Checklist de los 11 hallazgos de `agent-console`

Una sesión paralela (Gemini) corrigió 11 problemas de correctitud y consistencia en `web-app/src/features/agent-console/`, en el commit `4878e44` (*"fix(console): resolver los 11 puntos de consistencia, multimedia, huerfanos y refresco"*), fusionado vía el merge `0aebf2f`.

> [!warning] Esto es un checklist de verificación, no un backlog
> Los 11 ya están corregidos. Sirven para **re-verificar puntualmente si alguno reaparece** — por una regresión, o si el merge `4878e44`/`0aebf2f` se revierte o se rehace mal en una rama nueva. No investigar desde cero: ir directo al archivo y la línea.

1. Refresco tras guardar nota/mensaje reconstruye `notes: []` y pierde conversaciones — `agent-console.api-repository.ts:368-415`, `agent-console-command-runner.ts:54-77`.
2. Registros del mismo identificador se pisan porque `clients` se indexa por `personaIdentificador` en vez de por `caseId` — `agent-console.api-repository.ts:400-414`.
3. Cerrar un registro real descarta `outcome`/`qualityRating`; el historial de la API queda siempre vacío — `agent-console.api-repository.ts:413-415, 605-634`.
4. Todos los registros de la API mapeados como `"pending"` sin usar el catálogo real de `EstadoRegistro` — `agent-console.api-repository.ts:349-370`. **Confirmado corregido el 2026-08-26:** hoy usa `item.esTerminal ? "resolved" : "pending"` contra el catálogo real.
5. Una mutación puede tener éxito y fallar después el refresco → el usuario reintenta → posibles duplicados — `agent-console-command-runner.ts:54-77`.
6. Plantillas multimedia no envían `urlMedia`/MIME/nombre de archivo desde Agent Console, a diferencia del flujo standalone de Mensajes — `agent-console.commands.ts:24-28`, `MessageComposer.tsx:42-50`, `agent-console.api-repository.ts:521-537`.
7. Transferencia de registro usa agentes como si fueran `TeamId`, toma siempre el primer objetivo, equipo hardcodeado y silencia los errores del endpoint de agentes — `agent-console.api-repository.ts:391-395, 473-475`, `WorkspaceShell.tsx:143`, `InteractionPanel.tsx:104-107`.
8. La búsqueda por API crea registros sintéticos con controles editables que fallan con 404 al guardar — `agent-console.api-repository.ts:648-691`.
9. El mock tiene registros de "Chat interno" pero la UI oculta ese canal globalmente — divergencia mock/API — `data/mock/fixtures/ejemplo-a.ts`, `ejemplo-b.ts`, `InteractionPanel.tsx`, `shell.config.ts`.
10. El mock permite actualizar/eliminar plantillas globales o inexistentes sin error, a diferencia de lo que la API real probablemente rechazaría — `agent-console.mock-repository.ts:340-365`.
11. `MensajesPage`: carrera al cargar plantillas si se cambia rápido de conversación, pierde `mimeType` al enviar adjuntos y puede crear un registro huérfano si falla la tarea posterior — `MensajesPage.tsx:57-80, 89-97`, `PromoverMensajeModal.tsx:140-173`.

> El hallazgo #11 es el que originó la **regla permanente de mensajería** de `CLAUDE.md`: la resolución y validación de la entidad maestra (`EntidadId`) va **antes** del side-effect externo, nunca después.

---

## 4. Qué queda vivo de esto

- **Linajes paralelos:** el patrón se repitió después con `feature/diagramas-arquitectura-secuencia` y con las ramas de Codex. La regla que quedó de ahí — **comparar commits, no nombres de rama** — nació de un commit que aterrizó en la rama equivocada mientras Codex trabajaba en paralelo, y hoy vive en la memoria del agente (`feedback_verificar_rama_con_codex_en_paralelo`), no en el Playbook. Candidata a subir al Playbook como regla nueva.
- **Divergencia mock ↔ API:** los hallazgos 9 y 10 son la misma clase de bug. Mientras el mock siga siendo un repositorio paralelo escrito a mano, va a divergir.
- **Vista agregada sigue evolucionando en el backend:** los pendientes actuales (`DatosExternosEstado` falsy en el frontend, campos numéricos con sentinel 0, resiliencia asimétrica) están en [[TASKS|TASKS]] y en [[docs/guias/OBSERVACIONES-2026-09-03-INCIDENTES-Y-AUDITORIA|las observaciones del 2026-09-03]].

---

## Sobre esta nota

> [!note] Reconstrucción, no un retro escrito en el momento
> Tres notas del vault (`Home`, `Meta/sistema-multiagente-supervisado` y `TASKS`) enlazaban a `web-app/docs/retro-vista-agregada-agent-console.md` desde el 2026-08-24. Ese archivo **nunca se creó** — ni en `web-app/docs/`, ni en otra rama, ni en el historial del repo. Era un enlace fantasma: tres nodos apuntando al vacío.
>
> Este documento se escribió el **2026-09-09** para cerrar ese hueco, reconstruyendo los hechos desde las fuentes que sí quedaron: las filas de `TASKS.md` del 2026-08-22 al 2026-08-26 y la memoria del agente sobre el commit `4878e44`. Los commits, fechas y rutas citados vienen de ahí. Lo que no está registrado en ninguna de esas dos fuentes —el detalle de la discusión que llevó a extender `agent-console` en vez de duplicar— no se inventó: no está.
>
> **Vive en el vault (`docs/guias/`) y no en `web-app/docs/`** a propósito: el repo `AcmeOrg` es el que versiona el vault, así que una nota que tres notas necesitan tiene que estar versionada junto a ellas. En `web-app/` quedaría fuera del control de versiones del vault y podría volver a desaparecer.

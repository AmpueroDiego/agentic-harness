---
tipo: auditoria
fecha: 2026-09-11
tags: [auditoria, vault, documentacion, api-core, web-app, api-auth, api-contracts]
---

# Auditoría del vault contra el código — 2026-09-11

> Referencia histórica anonimizada: los hallazgos, rutas y estados describen el sistema fuente en la fecha indicada. No afirman que los repos de ejemplo existan en este checkout ni que sus incidencias sigan vigentes.


Pedido del responsable: validar todas las notas del vault de Obsidian contra el código. Nueve subagentes de solo lectura revisaron las 180 notas visibles contra `origin/develop` de cada repo (api-core `649eb13`, web-app `e837522`, api-contracts `a0bf5ed`, api-people `eba791a`, api-auth `97918e9`, api-delivery `f58e3279`, web-app-legacy `52643cb`) y contra las bases de dev por MCP en solo lectura. Registro en [[TASKS]].

**No se auditaron** (son registros: describen lo que era cierto en su fecha): los run docs `NNNN-*.md`, el export `docs/trello/`, `contexto-negocio/historico/`. En los logs fechados solo se revisó lo que afirman en presente.

**Resultado: ~1.300 afirmaciones verificadas, 205 discrepancias — 39 ALTA, 90 MEDIA, 76 BAJA.**

> [!note] Estado de las correcciones (2026-09-11, sin commit)
> - **Corregidas** las secciones **2, 4, 5 y 6** (todo lo que vive en la raíz de AcmeOrg). Cada hallazgo se re-verificó antes de editar; `validar-vault.py` en 0 errores. Dos ajustes a esta auditoría salieron de esa re-verificación: el reintento del Outbox **no** se prueba con un fallo transitorio (un timeout de PROVEEDOR_MENSAJERIA termina en `DeadLetter` sin reintentar — posible bug, ver C12) y `docs/pruebas/` no es solo local (`GUIA-APIDOG.md` y la colección sí se versionan).
> - **Pendientes, esperan decisión del responsable:** sección 1 (hallazgos de código), sección 3 (fuente única de ADRs), secciones 7-9 (repos api-core, web-app, api-auth, api-contracts, web-app-legacy: van por rama desde `develop`), la lectura directa por `DbContext` en `coder.md`/`planner.md`/`qa.md`, y `architect.md` L8-10 (`../api-contracts` no existe con cwd `AcmeOrg/`).
> - **Persona y Relacion:** solo lecturas por MCP; ningún cambio en sus repos ni en sus bases (pedido explícito del responsable).

Severidad: **ALTA** = alguien o un agente actuaría mal por creerlo · **MEDIA** = desactualizado relevante · **BAJA** = cosmético.

## 1. Hallazgos que no son de documentación

Salieron al contrastar las notas, pero son del código o de la base. Van aparte porque se resuelven con tarjeta o decisión, no editando un `.md`.

| # | Hallazgo | Evidencia | Qué implica |
|---|---|---|---|
| C1 | **Core tiene 2 FK con `ON DELETE CASCADE` hacia catálogo**: `FK_Registro_EstadoRegistro_EstadoRegistroId` y `FK_Registro_TipoServicio_TipoServicioId` | `sys.foreign_keys` en Core; `RegistroConfiguration.cs:25-26` no fija `OnDelete`; snapshot `:975,985` | La tarjeta Trello `<card-id>` y el playbook dicen "api-core ya está bien": falso. Borrar un estado o tipo de servicio borra registros en cadena |
| C2 | **Relacion tiene 13 FK con CASCADE, no 3**; Persona 13 sobre 39 FK, no 8 sobre 26 | `sys.foreign_keys` en Relacion (RELACION 3, MAESTRO 9, SERVICIO 1) y Persona (PERSONA 8, MAESTRO 4, RRHH 1) | La tarjeta `<card-id>` ("4 FK") se queda corta; varias van a catálogos (`Grupo→EstadoGrupo`, `Programa→UnidadMedida`, `ConfiguracionExterna→UnidadMedida`) |
| C3 | **CORS de api-core abre a cualquier origen con credenciales en cualquier ambiente** si `Cors:AllowedOrigins` llega vacío | `Program.cs:72-78`; `appsettings.json` trae `[ "" ]` | `CLAUDE.md` y ADR-0008 lo describen como "solo Development". En QA/Prod sin App Setting queda abierto |
| C4 | **Adjuntos del chat y canal "Chat interno" solo funcionan en mock** | `POST /api/Upload/Media` no existe en api-core; `canal:"Chat"` → `EnviarMensajeCommandHandler.cs:44-46` lanza (solo hay MensajeriaExterna y Correo) | Ya había tarjeta para adjuntos (`<card-id>`); el canal Chat no tiene ninguna |
| C5 | **web-app ignora `datosExternosEstado`** | cero referencias en `src` | Ya tiene tarjeta `<card-id>` |
| C6 | **RN-01 (no crear un registro si hay uno abierto) no está implementada** | `CrearRegistroCommandHandler` no valida duplicados | Decidir si es regla real |
| C7 | **Calificación de tarea: backend acepta 1-5, web-app manda malo=1, regular=3, bueno=5** | `CrearTareaCommandHandler`; `agent-console.api-repository.ts` | La regla documentada (1=Positivo) está al revés |
| C8 | Sección `Outbox:IntervalInSeconds/BatchSize` de `appsettings.json` no la lee nadie | job con 30 s y `TOP (20)` fijos | Configuración muerta |
| C9 | `ProcesarProcesoDominioCommandHandler` (api-contracts) valida y registra sin lock ni idempotencia | `:48-83` | Dos `Procesar` simultáneos pueden registrar ambas propuestas |
| C10 | Siguen versionados: clave JWT real en api-delivery (ya reportado 03/09) y clave de licencia Infragistics en web-app-legacy (`Instaladores/.../key.txt`) | — | Secretos en historial |
| C11 | api-auth: `Cors:AllowedOrigins` vacío **bloquea** navegadores (al revés que api-core) | `Program.cs:76-89` | Asimetría entre servicios |
| C12 | **Posible bug del Outbox: un fallo transitorio de PROVEEDOR_MENSAJERIA (caído/timeout) termina en `DeadLetter` sin reintentar** | Encontrado al corregir `CHECKLIST-DESPLIEGUE-OUTBOX-API-CORE.md` L106; sin verificar a fondo | Contradice el propósito del Outbox con reintentos; revisar `ProcessOutboxMessagesJob` y el handler de reintento |
| C13 | `Core.Mensaje.Direccion` es `nvarchar(20)` en la base, pero la API la devuelve como número | Encontrado al corregir `web-app-relacion-api-core.md` | Revisar la conversión en `MensajeConfiguration` |

## 2. Sistema multiagente — rutas que hacen fallar a los agentes

**Causa raíz:** los agentes corren con cwd `AcmeOrg/`, donde `docs/agent-runs/` casi no tiene nada y `docs/adr/` es una **copia vieja** (0001-0012). Las rutas sin prefijo `api-core/` leen lo equivocado sin avisar.

| Archivo | Línea | Problema | Sev. |
|---|---|---|---|
| `.claude/agents/retro.md` | 3, 12, 13, 62, 80 | `docs/agent-runs/RETRO-LOG.md`, `GOLDEN-TASKS.md` sin `api-core/`: concluiría que no hay log ni corridas | ALTA |
| `.claude/agents/coder-web.md` | 25 | Dice que las reglas 2-8 del frontend ya están en `CLAUDE.md`; solo están 3, las otras 5 viven en `adversary.md` (que no se autocarga) | ALTA |
| `.claude/commands/levantar-proyecto.md` | 33 | `preview_start name:"web-app"`: `launch.json` solo tiene `web-app-develop`/`web-app-mia`, y no hay herramientas `preview_*` en la CLI | ALTA |
| `.claude/agents/system-auditor.md` | 58 | `docs/agent-runs/SYSTEM-AUDIT-LOG.md` sin prefijo: declararía "primera auditoría" | MEDIA |
| `.claude/agents/architect.md` | 18 | `docs/adr/0004` resuelve a la copia vieja de la raíz | MEDIA |
| `.claude/agents/architect.md` | 31 | Usa `OutboxController` con `[Authorize]` pelado como ejemplo de algo a quitar; es riesgo aceptado | MEDIA |
| `.claude/agents/architect.md` | 34, 37 | Layout de carpetas descrito es el de api-contracts, no el de api-core (`Persistence/Configuration/Core/`, `Domain/Entities/Core/`, `Features/<F>/Command|Query/`) | MEDIA |
| `.claude/agents/planner.md` | 10, 62 | `docs/adr/` sin prefijo: no ve ADR-0013..0016 | MEDIA |
| `.claude/agents/coder-web.md` | 22 | Líneas de deuda `534, 900, 1116` → hoy `463-464, 830, 1046` | MEDIA |
| `.claude/commands/levantar-proyecto.md` | 34 | `.env.messaging-provider` no lo lee el compose: falta `--env-file .env.messaging-provider` | MEDIA |
| `.claude/agents/analyst.md` | 10, 22 | Denies están en `~/.claude/settings.json`, no en el del proyecto; `docs/agent-runs/` sin prefijo | BAJA |
| `.claude/agents/qa.md` | 18 | `docs/agent-runs/` sin prefijo | BAJA |
| `.claude/agents/ux-researcher.md` | 49 | `javascript_exec` no existe → `javascript_tool` | BAJA |
| `.claude/commands/orquestar.md` | 23, 167-171, 207 | "47 registros" (son 51); falta `docs/architecture/**` en la lista de `.gitattributes`; `api-core/docs/contexto-negocio/` no existe | BAJA |
| `coder.md:26,29`, `planner.md:40`, `qa.md:23` | — | Lectura directa por `ApplicationDbContext`/`ContractsDbContext` como último recurso (ya anotado en TASKS) | pendiente de decisión |

## 3. ADRs duplicados

`<org>/docs/adr/` (0001-0012) y `api-core/docs/adr/` (0001-0016) divergen **en los dos sentidos**: la raíz no tiene 0013-0016, tiene 0006 como `Accepted` (en api-core está `Superseded`) y 0004 sin sus addenda; api-core tiene 0011 más viejo que la raíz (le faltan las actualizaciones del 08/09). 0002, 0003, 0009 y 0010 son idénticos; 0001, 0005, 0007, 0008 y 0012 solo difieren en `tags`. `Home.md` (tabla Dataview) y los agentes leen la copia de la raíz.

**Propuesta:** fuente única en `api-core/docs/adr/`, trayéndole el texto de 0011 que hoy solo está en la raíz.

## 4. Notas de la raíz de AcmeOrg

### CLAUDE.md
- L14 — `api-delivery` = "DatosExternos" → dominio real: entrega de bienes y datosExternos (`Domain/Aggregates/{Participante,Elemento,DetalleExterno}`) — MEDIA
- L56 — `AdminSettings:*` en `""`/`REPLACE_ME` → `Email` e `IdAplicacion` tienen valor real a propósito; solo `Password` es secreto — MEDIA
- Sección CORS — "tolerante en Development" → ver C3: aplica en cualquier ambiente — MEDIA

### AGENTS.md
- L30 — `validar-vault.py` garantiza 0 enlaces rotos y frontmatter válido → no revisa frontmatter ni kebab-case; enlaces rotos solo avisan con código 0 — MEDIA

### README.md
- L50 — `docs/pruebas/` como contenido del repo → está en `.gitignore`, solo local — BAJA

### Home.md
- L77-84, 12, 122 — tabla de ADRs lee `docs/adr` (12) → la fuente viva es `api-core/docs/adr` (16) — MEDIA
- L8, 16 — "los 3 repos hermanos" → 6 más `web-app-legacy` — BAJA
- L56 — skill `explain-usage` → no existe — BAJA

### Meta/Graph-View-Config.md
- L154-164 — junction `comandos-pipeline/` "pendiente" → existe desde el 09/09 — MEDIA
- L170-175 — desde un worktree el hook avisa enlaces no resueltos → `validar-vault.py` salta rutas con "worktrees": escanea 0 notas, no valida nada — MEDIA
- L55, 157, 187 — "los 4 comandos" → 7 — BAJA
- L87 — `api-core/docs/mockups` no existe → existe, solo con `.html` — BAJA
- L112 — filtro `api-core/docs/.obsidian` → carpeta ya no existe — BAJA

### Meta/sistema-multiagente-supervisado.md
- L70, 57 — `retro` usa Haiku → `model: sonnet` — MEDIA
- L225 — `Core.OutboxMessage` y `BackgroundService` → `SERVICIO.OutboxMessage`, job de Quartz — MEDIA
- L228, 261 — dual-key BSUID + LID implementado → 0 resultados de `bsuid`; solo `@lid` — MEDIA
- L129 — 5 conectores en el planner → tiene 3 — BAJA
- L145 — cero eliminaciones = "Regla 4" → es la §8 del playbook — BAJA
- L29 — "6 conectores MCP" → 7 contando `azure` — BAJA
- L272 — `docs/agent-runs/GOLDEN-TASKS.md` → `api-core/docs/agent-runs/` — BAJA

### scripts/agentes-ia/
- `pipeline_graph.md` L13-45 — "máquina de estados exacta" → faltan `consulta_node`, `tier_0_node` y aristas a `retro` (`pipeline_orquestar.py:536-578`) — MEDIA
- `README.md` L31-35 — bloque `bash` con `Activate.ps1` → sintaxis PowerShell — BAJA

## 5. Guías y pruebas (`docs/`)

### PLAYBOOK-ANTI-REGRESIONES-Y-LECCIONES-APRENDIDAS.md
- L466, 478 — api-core sin CASCADE, "4 FK" a corregir → ver C1/C2 — ALTA
- L145 — `OutboxProcessorBackgroundService` → `ProcessOutboxMessagesJob` (Quartz) — MEDIA
- L365 — clave `CoreDb` → `ConexionSql` (`CoreDb` es fallback legado) — MEDIA
- L17-40 — índice de 22 reglas → existe §23 — BAJA
- L298 — `SecurityAuthorizeAttribute` con bypass Role_Master → clase `SecurityAuthorize`, sin bypass — BAJA
- L290 — `SignatureValidator` → no existe en develop; lección histórica — BAJA

### pruebas/README.md (local, ignorado por git)
- L134-138 — `/api/v1/Cliente/Buscar?query=`, `/api/v1/Relaciones/...`, `/api/v1/Mensajes/sin-asignar` → `GET /api/Cliente/Buscar?termino=`, `GET /api/MensajeriaExterna/SinAsignar`; relaciones está en api-contracts — ALTA
- L30 — webhook `/api/v1/Mensajes/webhook` + `x-webhook-secret` → `POST /api/MensajeriaExterna/Webhook` + `X-MessagingProvider-Webhook-Secret` — MEDIA
- L42 — claves `CoreDb`/`RelacionDb`/`PersonaDb` → solo `ConexionSql` — BAJA

### CHECKLIST-DESPLIEGUE-OUTBOX-API-CORE.md
- L106 — mensaje con "Status fallido" → no hay ese estado (1-5); usar `MensajeMensajeriaExternaFallidoDomainEvent` con fallo transitorio — MEDIA
- L96 — `IdAplicacion` en `CLAUDE.md` → solo está el email — BAJA

### PREPARACION-DEFENSA-CODE-REVIEW.md
- L9, 23 — PR #21 "abierto" → mergeado el 2026-09-03 (`808f30c`) — MEDIA
- L141 — tabla por script SQL → el camino principal es la migración — BAJA

### ESTANDAR-ENTREGA-TRELLO-Y-GITHUB.md
- L101 — el script "corta" la descripción → la rechaza — MEDIA
- L124 — `0010-resolucion-dinamica.md` → nombre real completo — BAJA

### pruebas/GUIA-APIDOG.md
- L13 — cubre "los 37 endpoints" → 35 de 37 (faltan los 2 de Outbox) — MEDIA
- L141 — Id "si se corrió el script" → mencionar la migración primero — BAJA

## 6. contexto-negocio/

### convenciones-bd-persona-relacion.md
- L88 — api-core sin CASCADE → ver C1 — ALTA
- L90-96 — api-contracts 3 cascadas → 13 (ver C2) — ALTA
- L98-101 — api-people 8 sobre 26 → 13 sobre 39 — MEDIA
- L45-58 — `BaseDomainModel` idéntico en los 3 repos → en relaciones/persona `FechaRegistro` no nulable; en persona `EsActivo` sin default — MEDIA
- L62 — `OutboxProcessorBackgroundService` → `ProcessOutboxMessagesJob` — MEDIA
- L114 — `IdUsuarioAsignado` sale del JWT → llega en el body; solo `AsignadoPor` sale del JWT — MEDIA

### reglas-negocio-registros-tareas-interacciones.md
- L101-102 — RN-07 con `RegistroEstadoCambiadoEvent`, `TareaCreadaEvent`, `MensajeRecibidoEvent` en `[Core].[OutboxMessage]` → no existen; el único evento es `MensajeMensajeriaExternaFallidoDomainEvent` en `[SERVICIO]` — ALTA
- L82 — calificación 1=Positivo → ver C7 — ALTA
- L80 — clasificaciones de ejemplo → ninguna existe en `MAESTRO.Clasificacion` (14 filas reales) — MEDIA
- L30-32 — RN-01 → no implementada (C6) — MEDIA
- L73-74 — `outcome`/`qualityRating` no se persisten → se persisten como Tarea de cierre (texto + calificación) — MEDIA

### api-delivery-arquitectura.md
- L114-115 — esquema `ENTREGA` con `EntregaElemento`, `PROCESAMIENTO.Operacion` → eliminado por `20260902060953_MoverLaEntregaDelElementoAlExpedienteDeProcesamiento`; hoy `OperacionProcesamiento`, `DetalleExterno`, `OrdenCompra`, `DocumentoExterno` — ALTA
- L26, 30 — agregados `EntregaElemento`, `Operacion` → `OperacionProcesamiento` y `DetalleExterno` — MEDIA
- L122 — api-core "separa por DbContext, mismo dbo" → un `CoreDbContext`, esquemas `Core`/`MAESTRO`/`SERVICIO` — MEDIA
- L107 — 63 tablas → 76 — BAJA
- L18 — api-people consume EDB → no; EDB llama a api-people — BAJA
- L71-73 — líneas de `UnitOfWork` → `65-93` y `95-112` — BAJA
- L42 — falta `EntidadesExternasController` — BAJA

### inventario-servicios-AcmeOrg.md
- L28, 33, 147 — URL de PROVEEDOR_MENSAJERIA por service discovery → se lee de configuración local (`MessagingProvider:UrlApi`…) — MEDIA
- L82 — api-core/api-contracts autentican por M2M → `POST api/Auth/Login` con email y password — MEDIA
- L103 — `DatosExternosDisponible` → `DatosExternosEstado` (Ok/Parcial/NoDisponible) — MEDIA
- L58, 70, 101 — consumidores incompletos → api-delivery consume relaciones y persona; api-contracts consume EDB — MEDIA
- L68, 154 — puerto de api-people UNVERIFIED → `3431` / `9001` — BAJA
- L37-39 — faltan `CorreoPollingBackgroundService` y `MensajesHub` — BAJA
- L41 — `DbContextEncapsulationTests` "fija" que no hay bases ajenas → solo impide usar `CoreDbContext` fuera de Persistence/Services — BAJA

### web-app-arquitectura-real.md — **toda la nota está superada**
Describe web-app "en blanco" (sin Axios, Zustand, Zod, auth ni tests, rutas `about`, `VITE_API_BASE_URL`). En develop hay features completas, `useMensajeStore`, clientes HTTP, `features/auth`, Zod, Vitest y `VITE_API_SEGURIDAD_URL`/`VITE_API_Core_URL`. Contradice a `web-app-arquitectura-frontend.md`, que es la correcta. **Propuesta:** marcarla como histórica y apuntar a la otra — ALTA (9 filas)

### web-app-arquitectura-frontend.md
- L26 — pendientes (api-repository, plantillas, bandeja, datosExternos) → ya están en develop — MEDIA
- L25 — "decisión pendiente #4" de architecture.md → ya no existe — BAJA

### web-app-relacion-api-core.md
- L40, 458 y ejemplos — respuestas en camelCase → **PascalCase** (Newtonsoft `DefaultContractResolver`, `Program.cs:25-28`); web-app convierte — ALTA
- L421-440 — POST/PUT Plantilla con JSON → `multipart/form-data` (`Titulo, Cuerpo, Canal, EsGlobal, TipoContenido, Archivo`; PUT con `EliminarArchivo`), 10 MB, jpg/png/webp/pdf — ALTA
- L442-454, 465 — base64 en `UrlMedia` → bytes en `ArchivoContenido varbinary(max)`; no existen `TemplatesPage` ni `readAsDataURL` — ALTA
- L38 — `src/services/api/http-core.ts` → `src/infrastructure/http/api-client.ts` — MEDIA
- L57 — solo el catch genérico tiene Details fijo → también 502/503/504 y `JsonException` — MEDIA
- L59 — el `Id` no tiene tabla → se guarda en `RequestResponseLog` (ADR-0016) — MEDIA
- L26, 461 — CORS en QA/Prod → ver C3 — MEDIA
- L111-118 — coasociado con 3 campos → también `celular`, `correo`, `direccion`, `direccionReferencia`; raíz con `datosExternosEstado` — MEDIA
- L240-242 — `CrearTareaRequest` → falta `MensajeId?` — MEDIA
- L363-367 — `Enviar` solo MensajeriaExterna → MensajeriaExterna y Correo; otro canal da 400 — MEDIA
- L413, 440 — enums sin verificar → `DireccionMensaje` Entrante=0/Saliente=1; `TipoContenidoPlantilla` con `Documento=4` — MEDIA
- L417 — EsGlobal no se valida → 403 si no es Supervisor — MEDIA
- L37, 348-351, 369-370, 4 — mecanismo JSON, `?tipoServicioId=`, respuesta de Vincular/Descartar, falta sección SignalR y `OutboxController` — BAJA

### Resto de contexto-negocio
- `seguridad-db-esquema-real.md` L54 — `RefreshTokens→Aplicacion` es CASCADE, no no-action — BAJA
- `modelo-bd-core.md` L143-182 — falta `EsActivo` en las 3 tablas de `SERVICIO`; sumar regla de borrado a la tabla de FKs — BAJA
- `README.md` L10 — nombra `web-app-mia` (eliminado) y omite `api-delivery` — BAJA
- `investigacion-meta-mensajeria-externa-bsuid-lid.md` L156 — `Destinatario` 150 → `nvarchar(256)` — BAJA
- `propuesta-core-resumen.md` L73 — `ClienteDetalleViewModel` no existe — BAJA

## 7. Repo api-core (se corrige por rama desde develop)

### CLAUDE.md
- L20 — opción 3 de lectura directa por `ApplicationDbContext`/`ContractsDbContext` → no existen ni hay cadena de conexión; exige diseño y ADR nuevos — ALTA
- L29, 62 — base `Core` atrasada → al día (29 migraciones, igual que develop); la rama local `fix/corregir-estado-migraciones-core-db` ya lo corrige — ALTA
- L22 — nunca POST → hay 4 POST de lectura (`BuscarRelacionIds`, `BuscarPorNombres`, `BuscarPorNumeroDocumento`, `DetalleCompletoPorIds`) — MEDIA

### README.md
- L17 — "EF Core 8", base `CoreDb` → EF Core 10.0.11, base `Core` — MEDIA
- L15 — capas sin `Services` — BAJA
- L23 — corridas 0001-0031 → 0001-0042 — BAJA

### api-core.IntegrationTests/README.md
- L12-17 — "los 3 tests" → 5 clases, 16 métodos (Outbox concurrency, locks de Mensaje) — MEDIA

### docs/PREGUNTAS-NEGOCIO.md
- L73 — `/api/Mensaje/SinAsignar`, `/api/Mensaje/{id}/Vincular` → `/api/MensajeriaExterna/...` — MEDIA
- L126 — #16 "resuelta parcialmente 04/09" → resuelta 07/09 — BAJA

### docs/agent-runs/
- `GOLDEN-TASKS.md` GT-02 — join directo a `relacion-db`: `ResumenRelaciones` no existe y contradice ADR-0004 → reescribir sobre `IApiRelacionService` — ALTA
- `GOLDEN-TASKS.md` GT-01 — datos desde `persona-db`, solo `[Authorize]` → HTTP vía `IApiPersonaService`, roles `Agente,Supervisor` — MEDIA
- `RETRO-LOG.md` L103-209 — bloque pegado dos veces (diff exacto) → quitar el duplicado — MEDIA
- `RETRO-LOG.md` L265-269 — 4 cambios "propuestos" → ya aplicados en coder/planner/qa/architect — MEDIA
- `RETRO-LOG.md` L61 — deuda de `ContractsDbContext` abierta → cerrada por eliminación — BAJA
- `INDEX.md` L9 — "47 registros" → 51 — BAJA
- `INDEX.md` L20, 22 — 0042 duplicada bajo Outbox → va en Mensajería y Migraciones — BAJA
- `INDEX.md` L161-162 — líneas en blanco rompen la tabla (0037-0042 fuera) — BAJA
- `INDEX.md` — sin fila para 0007 ni 0038 — BAJA
- `SYSTEM-AUDIT-LOG.md` — OK

### docs/adr/ (16)
| ADR | Estado declarado | Vigente en develop | Hallazgos |
|---|---|---|---|
| 0001 | Accepted | Parcial: sin lectura directa; USP a SistemaExterno nunca implementado | L34-36 ALTA, L40 MEDIA |
| 0002 | Accepted | Sí (MediatR 14.2.0) | L29 BAJA |
| 0003 | Accepted | Distinto: 6 proyectos (falta `Services`) | L25-27 MEDIA, L30 BAJA |
| 0004 | Accepted | Sí | L32/38 MEDIA (opción 3 exige reintroducir DbContext), L62 BAJA |
| 0005 | Accepted | Sí | L137-138 BAJA (action items hechos sin marcar) |
| 0006 | Superseded | Correcto | L13 BAJA (`Status: Accepted` en el cuerpo) |
| 0007 | Accepted | Sí; el Id se guarda en BD | L29 MEDIA |
| 0008 | Accepted | Sí; CORS más abierto (C3) | L65 MEDIA |
| 0009 | Accepted | Sí; firma cambió (`ResultadoEnvioCanal`, media) | L31 MEDIA |
| 0010 | Accepted | Parcial: 0012 lo cambió sin marcar | L30-33, 50-53, 77 MEDIA; L61 BAJA |
| 0011 | Accepted | Parcial | L42 columna `<list-id>` es "En revisión (Revisor Secundario)" ALTA; L43-46 miembros ALTA; L68 `trello.ps1` MEDIA |
| 0012 | Accepted | Sí | — |
| 0013 | Accepted | Parcial: 0014/0015 lo cambiaron | L144/183 `OutboxController` con roles (revertido) ALTA; L139 Dapper MEDIA; L120 siembra MEDIA |
| 0014 | Accepted | Sí | L44-46 firma BAJA |
| 0015 | Accepted | Sí | — |
| 0016 | Accepted | Sí | L119/129 BAJA |
| README | — | — | fila 0003 sin `Services` MEDIA; 0001/0010/0013 "Accepted" a secas MEDIA; títulos BAJA |

## 8. Repo web-app (se corrige por rama desde develop)

### docs/
- `pending-improvements.md` L42-44 — Mensajes sube y usa la URL → endpoint inexistente, falla siempre en API (C4) — ALTA
- `pending-improvements.md` L42 — Plantillas sube al seleccionar → ya va por FormData al guardar — MEDIA
- `product.md` L23 — chat interno → solo mock (C4) — MEDIA; L49 — api-core cubre "media" → no — MEDIA
- `roadmap.md` L29 — falta CI y tests de rutas → ya existen; falta coverage — MEDIA; L10 — adapter de Media apunta a endpoint inexistente — MEDIA
- `architecture.md` L8-15 — faltan Zustand y `@microsoft/signalr` — BAJA
- `agent-console-domain.md` L74-80 — firmas de commands incompletas — BAJA
- `README.md`, `AGENTS.md` — OK

### docs/review/
- `02-view-capabilities.md` L31 — adjuntos de hasta 25 MB → endpoint inexistente (C4) — ALTA
- `04-user-flows.md` L70-71 — plantillas suben con `MediaUploader` → multipart a `/api/Plantilla` — ALTA
- `06-api-and-data.md` L98 — `POST /api/Upload/Media` → no implementado — ALTA
- `10-risks-and-open-work.md` — faltan 3 riesgos: Upload/Media, canal Chat, `datosExternosEstado` — ALTA
- `02` L15 — plantillas con video → JPG/PNG/WebP/PDF 10 MB, video solo heredado — MEDIA
- `02` L4-5, 78-84 — igual en mock y API → las subvistas A, B y C y timeline vacíos en API — MEDIA
- `02` L52 — nota de datoExterno → `note: null`, sin `/api/NotaDatoExterno` — MEDIA
- `02` L62-63 — canales distintos de Llamada → Chat falla en API — MEDIA
- `02` L100, `06` L70-72, `08` L64-66, `10` L7-8 — Pendientes `[]` "por validar" → resuelto: filtra registros no terminales con asignación activa al usuario del JWT — MEDIA
- `01-project-map.md` L44 — UI de plantillas en `features/templates` → en `agent-console/views/TemplatesView.tsx` — MEDIA
- `08-development-runbook.md` L57-58 — falta exigir rol Agente/Supervisor — MEDIA
- `09-testing-guide.md` L48-50, `10` L23 — CI y tests de rutas/AuthProvider pendientes → existen; faltan coverage, lint en CI, re-run en synchronize — MEDIA
- `01` L25, 51-53; `02` L13; `06` L88, 97; `07` L42-43; `08` L5; `09` L18 — detalles de rutas, criterios de búsqueda, Node 22 — BAJA
- `README.md`, `03`, `05`, `11` — OK

## 9. Otros repos (se corrigen por rama en cada repo)

### api-auth
- `README.md` L33, 48, 258 — `ConnectController` `POST /connect/token` → no existe; `POST api/Auth/Token` form-urlencoded — ALTA
- `README.md` L67 — `PermissionAuthorizationHandler` con `perm` y `scope` → solo `perm` (usuario); `scope` lo evalúa `ScopeAuthorizationHandler` (máquina) — ALTA
- `docs/seguridad-unittests.md` L59-63 — tests 4 y 5 autorizan con `scope` → no existen; los reales prueban lo contrario — ALTA
- `README.md` L262-264 rutas de m2m-admin, L341 `Permissions.All`, L296-301 expiración en BD, L283-331 falta `Cors` y `Firebasesettings` — MEDIA
- `docs/seguridad-unittests.md` — 26 tests en 5 carpetas → 34 en 7 archivos — MEDIA
- `README.md` L56-65, 279, 19/92, 346-349; `m2m-data-model.md` L34, 57 — BAJA

### api-contracts
- `docs/proceso-dominio-workflow.md` L106 — revalidar resuelve la concurrencia → no hay lock (C9) — MEDIA
- `README.md` L5 — faltan enlaces a `proceso-dominio-workflow.md` y `AGENTS.md` — BAJA
- `docs/proceso-dominio-stored-procedures.md` L58-63 — Tipo 0/1/2/5 → el consumidor espera también 3, 4, 9 (SP en SistemaExterno, no verificable) — BAJA
- `AGENTS.md` — OK

### web-app-legacy
- `README.md` — no dice qué solución abrir (`AcmeCoreWebAzure/` vs `AcmeCoreWebProduccion/`) — MEDIA; título `# web-app`, `setup.rar` sin mencionar — BAJA

### api-delivery — estado de los planes del 2026-07-01
| Documento | Estado |
|---|---|
| plan `modelodominio-filtro-por-tipomodelo` | Implementado (`97a4b1d4`) |
| plan `tipomodelo-pertenece-a-marca` | Parcial: tareas 1-5 hechas; la 6 (`CategoriaElementoId` NOT NULL) no, en código ni en BD |
| spec `tipomodelo-pertenece-a-marca-design` | Implementado con la desviación nullable |

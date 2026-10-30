---
tipo: guia-pendientes
fecha: 2026-09-11
estado: backlog clasificado, listo para retomar
tags: [pendientes, backlog, consola-agente, web-app, api-core, demo, handoff]
---

# Pendientes de la consola del agente — corte del 2026-09-11

> 🏠 **Navegación:** [[TASKS|TASKS (Registro Vivo)]] · [[docs/adr/ejemplo-modelo-unificado|ADR-0017]] · [[contexto-negocio/modelo-actividad-entidad|Modelo de interacciones]] · [[docs/guias/guia-consola-pendientes-y-registros|Guía funcional de la consola]]

Ejemplo anonimizado de una sesión de demo en vivo con el responsable. Las entidades, rutas, datos y pantallas ilustran un dominio genérico; los estados y las mediciones son parte del ejemplo, no del estado actual de este repo. Se cortó por tiempo con todo especificado y nada a medias. Este documento es el punto de retomada: **cada pendiente está clasificado con archivo, línea y criterio de aceptación**, para poder lanzarlo sin volver a investigar.

---

## 1. Estado exacto al cortar

### Rama y worktree

| | |
|---|---|
| Worktree | `AcmeOrg/.worktrees/web-app--afinar-flujo-demo` |
| Rama | `feature/afinar-flujo-demo` |
| Commits locales | **6**, ninguno subido |
| Working tree | **10 archivos modificados sin comitear** (+ `routeTree.gen.ts`, ruido del dev server) |
| Build | ✅ verde — `tsc`, 191 tests y `eslint` pasaban al cortar |
| Push / PR | ❌ **no se hizo ninguno**, por instrucción del responsable |

```
<commit>  Filtrar la actividad por el servicio elegido al registrar una interacción
<commit>  Quitar la sugerencia vacía, mejorar el contraste y permitir elegir la referencia
<commit>  Corregir notas de entidad invisibles en la consola del agente
<commit>  Renombrar vista de detalle a actividad y hacer proporcionales los paneles laterales
<commit>  Quitar tarjetas de métricas de vista de detalle
<commit>  feat(agent-console): afinar flujo del registro, interacciones en actividad…
```

### Sin comitear (dos corridas terminadas y verdes)

| Corrida | Qué dejó |
|---|---|
| **Pestañas por canal + tarjeta compacta** | filtro `actividadCanalFilter` con pestañas y conteos, chip `{n}★`, asesor+fecha en una línea, `Fecha compromiso` a fila completa, y se quitaron los 3 botones "Simular adjunto" |
| **Punto de estado** | helper `esEstadoCerrado` + punto 🟢/🔴 en la esquina superior derecha de cada tarjeta, con `title` y `sr-only` |

> ⚠️ **Antes de comitear:** sacar `src/routeTree.gen.ts` del stage. Es generado por el dev server, no es un cambio real.

### Cambios en la base de dev (ya aplicados)

| Qué | Detalle |
|---|---|
| 3 filas en `DOMINIO.RegistroAsignacion` | ids `B1000001-…-0001/2/3`, `UsuarioRegistro = 'seed-demo'`, registros `REGISTRO-EJEMPLO`, `<otros-registros>`, asignados a `<id-ejemplo>` |
| `REGISTRO-EJEMPLO` **cerrado de verdad** | el responsable dijo dejarlo así. Estado `Cerrado`, 3 tareas (la tercera la creó el cierre), `Resumen` con la nota |

> El conector `core-db` **siempre reporta `affected_rows: 0`**, incluso cuando la escritura funciona. Verificar siempre releyendo la fila, nunca por el contador.

### Documentos escritos (sin comitear, en 2 repos distintos)

| Archivo | Repo | Estado |
|---|---|---|
| `docs/adr/ejemplo-modelo-unificado.md` | **api-core** | `??` sin trackear |
| `docs/adr/README.md` (fila del 0017) | **api-core** | ` M` modificado |
| `docs/guias/PENDIENTES-CONSOLA-AGENTE-2026-09-11.md` (este) | AcmeOrg | `??` |
| `docs/guias/guia-consola-pendientes-y-registros.md` | AcmeOrg | `??` |
| `contexto-negocio/modelo-actividad-entidad.md` | AcmeOrg | `??` (decisión #1 cerrada) |
| `Home.md`, `TASKS.md` | AcmeOrg | ` M` |

> ⚠️ **`api-core` está parado en la rama `fix/corregir-estado-migraciones`, no en `develop`.** El ADR quedó ahí sin comitear. Al retomar, decidir si se mueve a su propia rama antes de comitearlo.

> ⚠️ **Hay dos carpetas de ADR y solo una está viva.** `docs/adr/` es la canónica (llega a 0017); `AcmeOrg/docs/adr/` quedó congelada en 0012 y es una copia desactualizada. En esta sesión el ADR se numeró 0013 por error contra la copia vieja — el 0013 ya estaba tomado por `outbox-reintentos-quartz` — y se corrigió a 0017. **Vale la pena decidir qué se hace con la carpeta duplicada de la raíz**; hoy es una trampa para cualquiera que numere un ADR nuevo.


---

## 2. Pendiente A — 8 ajustes de UI *(especificado, listo para lanzar)*

Corrida de `coder-web` sobre el worktree. **Estaba lanzada y se canceló sin que tocara ningún archivo**, así que se relanza tal cual.

### A1 · Estrellas por tarea al registrar la interacción

**Archivo:** `src/features/agent-console/components/case-workspace/TicketForm.tsx`

Control **1–5 estrellas** abajo del formulario, misma fila que "Agregar a actividad" (calificación a la izquierda, botón a la derecha).

- **Opcional, default 5** — es lo que el sistema ya guarda hoy por detrás, así que no cambia datos.
- Accesible: `role="radiogroup"` + `aria-label`, cada estrella `role="radio"` con `aria-checked` y `aria-label` ("3 estrellas"), roving `tabIndex` como `moveTabFocus` en `workspace-helpers.ts`.
- El valor viaja por el mismo mecanismo que `ticketDraft` usa para servicio/actividad/referencia/estado.
- **Rastrear cómo llega hoy `Calificacion` al backend antes de inventar nada** — el repositorio ya la manda (las tareas existentes tienen 4 y 5 en la base).

### A2 · Quitar la calificación por colores del cierre

**Archivo:** `src/features/agent-console/components/case-workspace/CloseCaseDialog.tsx`

Eliminar el bloque **"¿Cómo calificas esta atención?"** (Verde / Amarillo / Rojo). el responsable: *"es como las estrellas"*.

El modal conserva: nota de cierre, **Resultado del registro** y "Últimas atenciones de este entidad".

> ⚠️ `closeCase` (`agent-console.api-repository.ts:920`) valida `input.qualityRating || input.note || input.outcome` para exigir clasificación. Al quitar el rating **ese guard no puede volverse más laxo**: debe seguir disparando por `note`/`outcome`.

### A3 · GUIDs crudos en el modal de cierre

**Archivo:** `CloseCaseDialog.tsx` — el primer paso muestra hoy:

```
Servicio     <id-ejemplo>
Estado       <id-ejemplo>
Actividad    <id-ejemplo>
```

Debe mostrar nombres legibles. Los catálogos ya están en el estado (las mismas listas que llenan los `<select>` de `TicketForm.tsx`). Si un id no resuelve: fallback legible, **nunca el GUID**.

*La pantalla cuyo único propósito es que el agente confirme qué cierra, es justo la que hoy no se puede leer.*

### A4 · La tarjeta no refresca al agregar una tarea

**Reproducido en vivo.** Se agrega la tarea, la API la guarda bien (verificado en base), pero la tarjeta sigue mostrando `TAREAS / ACTIVIDADES (1)`; solo muestra `(2)` tras recargar.

Refrescar `session.registrosEntidad` cuando el comando resuelve OK. **Seguir el patrón de los comandos que sí refrescan** (`addNote`/`updateNote`), no inventar uno. Nada de `window.location.reload()`.

### A5 · `Cierre (resolved)` sin traducir

**Archivo:** `src/features/agent-console/data/agent-console.api-repository.ts:959`

```ts
`Cierre (${input.outcome}): ${input.note}`   // → "Cierre (resolved): …"
```

Mapear: `resolved` → "Resuelto", `follow_up_required` → "Requiere seguimiento", `unresolved` → "No resuelto".

**No cambiar el tipo del dominio** (`CaseOutcome` en `src/domain/cases/case.ts` sigue en inglés). Función pura + test, cubriendo outcome desconocido.

### A6 · Botón para traer un registro abierto al frente

**Archivo:** `AccountTabs.tsx`, tarjetas de la actividad.

Pedido del responsable: poder abrir un registro desde la actividad como pestaña de trabajo y agregarle una tarea, sin volver a Pendientes.

- **Solo en registros no cerrados** — usar `esEstadoCerrado` de `workspace-helpers.ts`.
- Si ya está abierto como pestaña, **activarla, no duplicarla**.
- **Reusar `OpenCaseButton`** (`src/features/agent-console/components/views/ViewActions.tsx`), que es el de "Abrir registro" de Pendientes. No duplicar la lógica.
- Texto corto ("Abrir") o ícono con `aria-label`, sin romper la compactación.

### A7 · Fecha compromiso no se ve en las tarjetas

El formulario la pide pero no aparece en ninguna parte de la actividad.

**Primero verificar si el dato llega al front** (`RegistroEntidadDto` / DTO de tarea). Puede que ni se mapee desde la API.
- Si llega → mostrarla compacta, **solo cuando tenga valor** (nunca un "—" ocupando espacio).
- Si no llega → **reportarlo como bloqueo, no inventarlo**. Se convierte en cambio de backend (~15 min extra).

### A8 · Compactar "Responder con plantilla" a 2 líneas

Hoy ocupa 3 filas: label+`<select>`, `<textarea>`, footer con hint + "Enviar".

Forma objetivo:
```
[ Elegir plantilla ▾ ]   [ textarea .............................. ]
Se reemplazan automáticamente nombre y monto.          [ ✈ Enviar ]
```

- El label visible se puede quitar, pero el `<select>` **conserva nombre accesible** (`aria-label`) y el `<label for=...>` no puede quedar apuntando a nada.
- Mantener el apilado en `app-phone:`.
- El `<textarea>` sigue redimensionable y con su `aria-label`.

---

## 3. Pendiente B — Interacción unificada (ADR-0013)

**Decidido por el responsable**, ADR escrito en [[docs/adr/ejemplo-modelo-unificado|ADR-0017]] (estado *Proposed*).

### El modelo

```
              ENTIDAD (Entidad)
                     │
        ┌────────────┴────────────┐
      REGISTRO                   INTERACCIÓN
   (problema)              (lo que pasó)
   estado, SLA,                  │
   cierre  ◄──── RegistroId (opcional, = WhatId)
```

| Campo | Regla | Referencia externa |
|---|---|---|
| `EntidadId` | **NOT NULL** | `WhoId` |
| `RegistroId` | **NULL** | `WhatId` |
| `Tipo` | `1 = Tarea`, `2 = Evento` | Task / Event |
| `Canal`, `ClasificacionId`, `Detalle`, `Fecha`, `Calificacion`, `IdUsuarioAgente`, `Origen` | | |

### Invariantes que no se pueden romper

1. `EntidadId` siempre presente.
2. Si `RegistroId` no es NULL, su `EntidadId` **debe coincidir** con el del registro.
3. Un `Evento` no tiene ciclo de vida: sin estado, sin cierre, sin asignación, sin calificación.
4. Un `Evento` **nunca** entra a `GET /api/Registro/Pendientes`. Esa cola es de registros, no de hechos.

### Alcance acotado por el responsable

> *"tipo de eventos pone evento de ejemplo, lo manda un api externa al dominio, ahora no hagas el endpoint solo déjalo en BD no más y que el api lo muestre"*

| Pieza | ¿Entra? |
|---|---|
| Tabla + migración + copia de las 16 tareas | ✅ |
| Lectura: eventos en actividad y vista de detalle | ✅ |
| Semilla dev: `Evento de ejemplo`, `Otro evento de ejemplo` | ✅ |
| Render **celeste plano** en web-app, intercalado por fecha | ✅ |
| **Endpoint `POST` de creación** | ❌ **no** — lo llenará una API externa |
| Integración real con un proveedor externo | ❌ no |

### Render pedido

```
┌ ● Actividad de ejemplo  REGISTRO-EJEMPLO  mensajería    🔴 ┐
│   Asesor: Operador de ejemplo                     11 set. 2026, 05:04 p.m.
│   ✓ TAREAS / ACTIVIDADES (3)
└──────────────────────────────────────────────────────────────────┘

  ▎ Evento de ejemplo · Canal externo             10 set. 2026, 09:15 a. m.   ← celeste
    Ocurrió una actividad del dominio · Operador de ejemplo
```

**Caja = expediente vivo. Franja celeste = algo que ya pasó.** El evento no lleva caja, ni punto de estado, ni tareas anidadas, ni calificación, ni botón de cerrar.

### Costo medido

| | |
|---|---|
| Filas a migrar | **16** tareas activas, 12 registros |
| Endpoints afectados | **2** — `POST`/`GET /api/Registro/{id}/Tarea` (`Rest/Controllers/RegistroController.cs:66,77`) |
| Impacto en el frontend | **ninguno**, los endpoints conservan contrato |

### Plan (8 pasos, el 8 va en entrega aparte)

1. Entidad `Interaccion` + configuración **explícita por entidad** (nunca `ApplyConfigurationsFromAssembly`)
2. Migración EF: tabla + índices por `EntidadId` y `RegistroId`
3. Copia de las 16 filas, resolviendo `EntidadId` desde `Registro`
4. Los 2 endpoints pasan a leer/escribir `Interaccion` con `Tipo = 1`, sin cambiar contrato
5. Los eventos salen en actividad y vista de detalle
6. Semilla en dev
7. Render celeste en web-app + conteo en pestañas de canal
8. **Retiro de `DOMINIO.Tarea` — migración aparte, solo tras validar.** No en la misma entrega.

> ⚠️ **Ninguna API auto-migra.** Aplicar a mano en dev y Azure; el fallo es silencioso.
> ⚠️ La migración toca `ModelSnapshot`: coordinar con cualquier otra rama abierta que genere migraciones.

---

## 4. Pendiente C — Arreglar Pendientes

Tres bugs vistos en vivo, todos en `src/features/agent-console/data/agent-console.api-repository.ts`.

| # | Bug | Dónde | Arreglo |
|---|---|---|---|
| C1 | **ENTIDAD muestra el identificador fiscal**, no el nombre | `:704` usa `registro.entidadDocumento` | traer el nombre. El agente ve `<identificador-entidad>` y no sabe a quién va a atender |
| C2 | **TIEMPO EN COLA siempre vacía** | `:707-708` — `wait: ""`, `warning: false` hardcodeados | columna muerta, y es **justo la del SLA**. Definir desde cuándo se cuenta: creación del registro o asignación |
| C3 | **"Canal externo" se rotula "Chat interno"** | `mapCanalToChannel:134` solo reconoce messaging/correo/llamada; **todo lo demás cae en `chat`** | el responsable ya dijo que chat interno no va |

**Además (C4):** el "Asesor" de las tarjetas sale de `Registro.Autor`, un **texto libre** — no de la asignación. Son cosas distintas (quién lo creó vs. quién lo tiene) y la UI solo muestra la primera. Si se transfiere el registro, el nombre no cambia.

### Hueco de diseño, no bug

**No existe cola general de registros sin asignar.** `Pendientes` es "mis registros asignados", no "registros por tomar". Un registro recién creado no está asignado a nadie, así que **es invisible para todos**: no aparece en ninguna pantalla.

Hoy hay 7 registros en ese limbo (solo los 3 sembrados a mano son visibles).

Salidas: un endpoint de cola sin asignar, o auto-asignar al crear. **Decisión del responsable, no técnica.**

---

## 5. Pendiente D — Arreglar Historial

**El Historial es falso.** `state.history` sale de `localClosedHistory`, **un array en memoria** (`agent-console.api-repository.ts:60`), que se vacía al recargar y al cerrar sesión.

**Demostrado en vivo:** se cerró `REGISTRO-EJEMPLO`, el Historial mostró 1 fila, **se recargó la página y volvió a 0** — con el registro cerrado en la base.

Consecuencia: **un agente no puede ver mañana lo que cerró hoy.** Solo lo encuentra entrando entidad por entidad a la actividad.

**Requiere endpoint nuevo en api-core** (registros cerrados por usuario, paginado) — hoy no existe. Es el pendiente más caro de los tres de arriba.

---

## 6. Pendiente E — Botón "Transferir" muerto

`transferTargets: []` está **hardcodeado vacío** en `agent-console.api-repository.ts:757`. `WorkspaceShell.tsx:176` lee `data.transferTargets[0]?.id` → `undefined` → el handler aborta y sale el toast *"No hay un equipo de transferencia disponible"*.

**No hay selector de agente, ni lista de equipos, ni endpoint que devuelva agentes disponibles.**

El backend en cambio **está bien resuelto**: `AsignarRegistroCommandHandler` hace reasignación real con historial (cierra la anterior con `FechaFin` + `EstaReasignado`, crea la nueva con `AsignadoPor` del JWT, y una restricción única impide dos activas a la vez).

Falta solo la UI y el endpoint que liste agentes.

---

## 7. Pendiente F — QA + adversary final

**No correr hasta que el responsable diga que cerró la agenda.** Su instrucción: *"al final no más se corrigen los bugs, porque voy agregando agenda… sino le paso todo QA y adversary múltiples veces"*.

Cuando toque: **los dos en el mismo mensaje**, en paralelo, sobre el diff completo acumulado.

### Ya escalado de antes, sin corregir

**P1 de paridad:** `agent-console.mock-repository.ts:208` no propaga `tipoServicioId`, así que **en modo mock el filtro Servicio→Actividad no discrimina**. No afecta la demo (corre contra la API real, probado por las llamadas a `localhost:5182`). Fix estimado: 1 línea + test.

**Regla que dejó:** todo campo nuevo en `TicketOption`/`CatalogoItem` debe tocar **las dos** implementaciones del repositorio.

---

## 8. Fuera de código — depende del responsable

| Qué | Por qué |
|---|---|
| **Rotar la contraseña SQL de `core-db`** | quedó expuesta en sesión el 2026-09-11 |
| **Renombrar la tarjeta Trello `<card-id>`** | a "Agregar InteraccionEntidad para contactos sin registro (api-core, web-app)". El estándar prohíbe que la toque un agente |
| **Decidir la cola general** | endpoint de sin-asignar vs. auto-asignar al crear |
| **Decidir el gate de cierre** | ver abajo |

### El gate de cierre

Hoy `closeCase` **ya exige clasificación, pero solo si** hay calificación, nota o resultado. **Cerrar en blanco pasa sin ninguna validación** — está al revés.

Propuesto (en api-core, no en el front, para que valga desde cualquier origen):

| Requisito para pasar a `Cerrado` | Hoy | Propuesto |
|---|---|---|
| Clasificación | solo si hay nota/rating | **siempre** |
| Al menos 1 tarea en actividad | no | **sí** |
| Actividad coherente con el servicio | solo en el front | **también en backend** |
| Pasar por `Atendido` antes de `Cerrado` | no | opcional — decidel responsable |

---

## 9. Orden sugerido al retomar

| # | Qué | Estimado |
|---|---|---|
| 1 | **Pendiente A** (8 ajustes de UI) — relanzar tal cual, está especificado | 10–15 min |
| 2 | **C + D + B en una sola corrida de api-core** — una migración y un solo ciclo de build en vez de tres | ahorra 20–25 min |
| 3 | Render celeste en web-app | ~10 min |
| 4 | **F** — QA + adversary en paralelo, y corregir hallazgos | 10 min + lo que salga |
| 5 | `/worktree sincronizar` (merge de develop + build sobre el código combinado) | |
| 6 | Commit, push y PR **solo cuando el responsable lo pida** | |

**Total estimado: 2 a 2½ horas** de trabajo de agentes.

> **No paralelizable:** todo el frontend cae en el mismo worktree y los mismos archivos; dos `coder-web` a la vez se pisan.

---

## 10. Para levantar el ambiente

| Servicio | Puerto |
|---|---|
| `api-core` (Host) | `5182` |
| `web-app` (Vite) | `5173` |

Usuario ficticio de la demo: `<usuario-demo>`, rol `Agente`, id `<id-ejemplo>`.

Si la consola carga pero sale todo vacío, el problema casi siempre es el `5182`, no el front.

> **Bug de sesión conocido:** `POST /api/Auth/RefreshToken` → 400 y logout. Causa: rotación sin gracia + una cookie por perfil de Chrome + web-app refrescando en cada carga. Tarjeta `<card-id>`.

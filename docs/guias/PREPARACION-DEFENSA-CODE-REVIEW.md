---
tipo: guia
fecha: 2026-09-03
tags: [guia, code-review, api-core, outbox, logging, defensa]
---

# Preparación para la revisión: qué te pueden preguntar de lo que ya está subido

Ejemplo anonimizado de un banco de preguntas anticipadas sobre **PR de Outbox** (Outbox con reintentos, ya mergeado a `develop`) y **PR de logging** (RequestResponseLog, mergeado a `develop` el 2026-09-03 en `<commit>`; estaba abierto cuando se escribió esta guía). Cada entrada trae la respuesta corta para decir en voz alta, y el dato duro por si insisten.

---

## 0. El marco de apertura (decilo vos primero, antes de que pregunten)

> "Subí dos cosas. Uno: el Outbox con reintentos, homologado literal con `api-delivery` — eso fue decisión tomada con Revisor Principal, está en ADR-0014 y ADR-0015. Dos: trazabilidad de errores — cuando la API devuelve un `Id` de error, ese `Id` ahora existe en una tabla y soporte lo puede buscar; antes era un Guid que no estaba en ningún lado. Todo lo que se aparta de `api-delivery` está registrado como divergencia deliberada en un ADR, no es improvisación."

**Tu carta más fuerte es esa:** cada decisión rara tiene un ADR con el trade-off escrito. Si alguien cuestiona una elección, la respuesta no es defenderla de memoria, es abrir el ADR.

**Números para tener a mano:**

| | PR de Outbox (Outbox) | PR de logging (RequestResponseLog) |
|---|---|---|
| Estado | Mergeado a `develop` | Mergeado a `develop` (2026-09-03) |
| Archivos | 93 | 25 |
| Líneas | +6584 / −269 | +2403 / −30 |
| ADRs | 0013, 0014, 0015 | 0016 |

---

## A. Outbox (PR de Outbox)

### A1. ¿Por qué Dapper acá, si el resto del repo usa EF Core?

**Respuesta:** ADR-0014 — paridad con `api-delivery`, que usa `ISqlConnectionFactory` + Dapper para su job. Y hay una razón técnica propia: reclamar filas necesita hints de bloqueo (`UPDLOCK`, `READPAST`) que EF Core no expresa.

### A2. Si el App Service escala a 2 instancias, ¿no procesan el mismo mensaje dos veces?

**Respuesta:** No. El reclamo es `SELECT TOP (20) ... WITH (ROWLOCK, UPDLOCK, READPAST)` dentro de transacción: la segunda instancia **saltea** las filas que la primera ya tiene bloqueadas en vez de esperarlas. Además `[DisallowConcurrentExecution]` evita que el mismo job se solape dentro de un proceso.

**Si insisten:** el `READPAST` es una divergencia respecto de `api-delivery`, y está documentada como tal en ADR-0015.

### A3. ¿Y si el proceso se muere en medio del envío? El mensaje queda en `Processing` para siempre.

**Respuesta:** Para eso está `RecuperarZombisAsync`. Levanta los mensajes que llevan más de `ZombiRecoveryMinutes` en `Processing` y, según la política, los reprograma como reintento o los manda a `DeadLetter`. Corre al inicio de cada ciclo, antes de reclamar mensajes nuevos.

### A4. ¿Cuántos reintentos y cada cuánto?

**Respuesta:** Configurable **por tipo de evento** en `[SERVICIO].[OutboxRetryPolicy]` — hay una política `DEFAULT` y una específica para mensajería. El job corre cada 30 segundos y toma lotes de 20.

**Si insisten:** el backoff se calcula en `double` con clamp, justamente para que un `RetryCount` alto no desborde el `int` (lo encontró la auditoría adversarial, no salió gratis).

### A5. ¿Reintentar no duplica mensajes de mensajería al cliente?

**Respuesta:** Hay un clasificador que distingue fallo transitorio (red, timeout, códigos de Azure SQL) de fallo de negocio: el transitorio se reintenta, el de negocio va directo a `DeadLetter` sin reintentar.

**Sé honesto acá:** el problema de los 2 generales no está resuelto end-to-end. Si el proveedor de mensajería recibió el mensaje y la respuesta se perdió en el camino, el reintento lo manda de nuevo. Es **riesgo residual aceptado**, no hay idempotencia con clave de negocio contra el proveedor de mensajería. Si te lo marcan, es un hallazgo válido — anotalo, no lo discutas.

### A6. ¿Por qué `Status` es un `int`? En SSMS no se entiende nada.

**Respuesta:** Es exactamente el trade-off que discutimos con Revisor Principal y quedó decidido en ADR-0015: paridad literal con `api-delivery` pesa más que la legibilidad local, porque los devs rotan entre microservicios.

**Llevá el mapeo anotado, el orden NO es el obvio:**

| Valor | Estado |
|---|---|
| 1 | Pending |
| 2 | Processing |
| **3** | **ScheduledForRetry** |
| **4** | **Processed** |
| 5 | DeadLetter |

### A7. ¿Por qué el job le pregunta a api-auth si está activado?

**Respuesta:** Flag `API_CORE_JOB_OUTBOX_ACTIVADO`, para poder apagar el worker sin redeploy.

**El contra que te pueden tirar (y tienen razón):** si api-auth no responde, o el flag no existe en ese ambiente, el job **se saltea el ciclo en silencio** — solo queda un `LogWarning`. Es fail-closed, que está bien (nada se pierde, los mensajes quedan en `Pending` y se retoma al siguiente ciclo de 30s), pero **en un ambiente donde nadie creó el flag, el Outbox nunca corre y nadie se entera.** Respuesta honesta: "es deliberado fail-closed, pero coincido en que falta una alerta; si el flag no está definido hoy se comporta igual que apagado."

---

## B. RequestResponseLog (PR de logging)

### B1. ¿Por qué una tabla nueva y no Application Insights / Serilog?

**Respuesta:** Dos razones. Paridad: `api-delivery` ya tiene esa misma tabla y ese mismo patrón. Y el caso concreto que lo originó: soporte necesita poder buscar el `Id` que la API le devolvió al cliente, sin acceso al portal de Azure.

### B2. ¿No estás guardando el password del admin en texto plano?

**Esta es la mejor pregunta que te pueden hacer, y ya está resuelta — contestala con seguridad.**

**Respuesta:** No. `RequestBody` **nunca se popula**, para ningún request. La columna existe únicamente por paridad de esquema con `api-delivery`, y está documentado en la entidad para que nadie la "complete" pensando que fue un olvido. El diseño original sí lo hacía — `ApiAuthService` manda `Email`/`Password` de `AdminSettings` en el body del login — y por eso se acotó a: solo camino de error, y nunca body de request. ADR-0016.

### B3. Pero el header `Authorization` sí lo guardás.

**Acá tenés que ser preciso, porque la respuesta es "depende de cuál", y si simplificás te agarran.**

- **Request entrante** (`ExceptionMiddleware`): **no**. Se excluyen `Authorization`, `Cookie` y `Set-Cookie`, y se enmascaran `access_token`, `token`, `id_token`, `api_key` del query string — esto último no es teórico: SignalR manda el JWT por la URL en `/hubs` porque no puede mandar headers en el handshake. Es divergencia deliberada de `api-delivery`, aprobada, ADR-0016 §5.
- **Llamada saliente** (`RequestResponseLoggingHandler`): **sí**, se serializan los headers completos, incluido el `Bearer` del token de sistema. Es paridad literal con `api-delivery` y está declarado como **riesgo aceptado** en ADR-0016 §3 — el mismo riesgo que ya corre `api-delivery` en producción hoy.

**Decilo así, sin taparlo:** "En entrantes lo saqué. En salientes lo dejé por paridad con el servicio hermano y está escrito como riesgo aceptado. Si el criterio del equipo es sacarlo también ahí, lo saco, pero entonces conviene sacarlo en el servicio hermano también."

### B4. La tabla no tiene índices y todo es `nvarchar(max)`. ¿Cómo la consultás con millones de filas?

**No tenés respuesta y no la inventes.**

**Respuesta:** Hoy solo tiene la PK sobre el `Id` (`uniqueidentifier`). La consulta principal —buscar por el `Id` que se le devolvió al cliente— sí pega contra la PK, que es el caso de uso que motivó todo. Las consultas de soporte por `Timestamp` o `CorrelationId` hacen scan. **No está resuelto.** Lo natural es un índice non-clustered en `Timestamp DESC` y otro en `CorrelationId` cuando el volumen lo justifique.

**Si te aprietan más:** una PK clustered sobre un GUID aleatorio en una tabla append-only fragmenta. Es paridad con `api-delivery`; si el volumen molesta, se pasa a clustered por `Timestamp` + non-clustered en `Id`.

### B5. ¿Y la retención? ¿Quién limpia esa tabla?

**Tampoco tenés respuesta, pero tenés un buen mitigante.**

**Respuesta:** No hay purga hoy. El mitigante real es que **solo se escribe en camino de error**, no en cada request — el volumen es proporcional a los fallos, no al tráfico. Igual falta un job de purga a N días; lo asumo como pendiente.

### B6. Fire-and-forget en el handler: ¿no perdés logs si el proceso se recicla?

**Respuesta:** Sí, se pueden perder. Es deliberado: el logging es operacional y no puede demorar la llamada real (autenticación, una consulta del dominio, mensajería) si CoreDb está lenta o caída. El `Task` descartado tiene `try/catch` en todo su cuerpo, así que nunca queda una excepción sin observar.

**Ojo, el `ExceptionMiddleware` es distinto:** ahí **sí se espera** el INSERT antes de responder, para que cuando el cliente reciba el `Id` la fila ya exista.

### B7. ¿Entonces le agregás latencia a cada respuesta de error?

**Respuesta:** En el caso normal es un INSERT de milisegundos. La espera está acotada a **3 segundos**: si CoreDb está lenta —escenario realista, porque el mismo incidente que tumbó al servicio dependiente puede afectarla— se deja de esperar y se responde igual; el INSERT sigue en background y la fila aparece unos segundos después. El tope existe para no convertir un fail-fast en un fail-slow de ~45s, que son los timeouts default de SqlClient.

### B8. ¿Por qué creás un scope de DI nuevo en vez de usar el de la request?

**Respuesta:** Porque el scope de la request que acaba de fallar puede tener un `DbContext` con cambios a medio aplicar o una conexión en mal estado. Un scope limpio aísla el logging de ese estado. Es divergencia deliberada respecto de `api-delivery`, que usa `context.RequestServices` y por eso necesita un `ClearTrackedChanges()`.

### B9. ¿Por qué el PR tiene 2400 líneas para algo tan chico?

**Respuesta:** ~1042 son el `.Designer.cs` autogenerado de la migración de EF Core, ~500 los tests nuevos, ~150 el ADR y ~110 los diagramas C4. **Código productivo real: alrededor de 450 líneas** — el handler, el middleware, la entidad, la config y el repositorio.

**Dato útil:** el `.gitattributes` ya colapsa en la vista de diff los `agent-runs`, los ADRs, los `.Designer.cs` y los proyectos de test, justamente para que el revisor vea el código y no el ruido.

---

## C. Despliegue y proceso

### C1. ¿La tabla se crea sola al desplegar?

**Respuesta:** No, y es a propósito. Ninguna API de AcmeOrg ejecuta `Migrate()` al arrancar — es la regla 17 del Playbook. La tabla la crea la migración `<fecha>_AgregarRequestResponseLog`, y se aplica con `dotnet ef database update` como cualquier otra. Solo si en ese ambiente no se puede correr EF hay un script idempotente, `scripts/crear-request-response-log.sql`, que crea la tabla si no existe **y además inserta la fila en `__EFMigrationsHistory`** para que EF no intente recrearla después.

### C2. ¿Existe un pipeline que aplique migraciones?

**Respuesta honesta:** Verifiqué que ningún workflow de GitHub Actions de los 4 repos lo hace, y que ninguna app llama `Migrate()`. Lo que **no** pude descartar es un pipeline externo de Azure DevOps. Está como pendiente: revisar el Deployment Center del App Service o preguntarle a el responsable de infraestructura.

### C3. ¿Esto lo probaste?

**Respuesta:** Dos suites nuevas de tests (`ExceptionMiddlewareTests`, `RequestResponseLoggingHandlerTests`), incluido el caso de CoreDb caída donde el cliente igual recibe su 502. Y una suite en Apidog de 51 requests cubriendo los 37 endpoints, corrida en local con un JWT real.

### C4. ¿Ya sabés por qué falla el 502 en dev?

**Respuesta:** Todavía no, y esto es exactamente lo que lo va a decir. En local funcionan los 37 endpoints; la cadena de api-auth resuelve bien. La diferencia tiene que estar en las Application Settings del App Service. Falta correr el script en dev y leer la fila del error — hasta ahora el `Id` que devolvía no existía en ninguna tabla, que es el hueco que cierra este PR.

### C5. ¿Quién revisó esto antes de subirlo?

**Respuesta:** El pipeline architect/planner/coder/qa más una auditoría adversarial. En esta rama el adversary encontró **3 defectos reales** y los tres están corregidos: fuga de JWT por `?access_token=` en `/hubs`, fail-slow sin tope en la persistencia, y campos sin cota de longitud. Cada corrida está documentada en `docs/agent-runs/`.

---

## D. Las 5 donde te van a hacer doler (asumilas rápido, no las pelees)

1. **Índices** — la tabla solo tiene la PK. Consultas por fecha o correlación hacen scan.
2. **Retención** — no hay purga; crece indefinidamente.
3. **`Authorization` en salientes** — sí queda en el log de las llamadas fallidas. Riesgo aceptado, documentado, pero es un hallazgo válido.
4. **Duplicidad en mensajería** — el reintento puede reenviar si la respuesta del proveedor de mensajería se perdió. No hay idempotencia end-to-end.
5. **Flag del Outbox** — si el flag no existe en un ambiente, el job nunca corre y solo queda un warning.

**Cómo contestar cuando no tenés la respuesta.** No improvises un diseño en la reunión. Usá esta forma:

> "No lo resolví. Está identificado, es *[X]*, y el impacto es *[Y]*. Lo hago en esta misma rama o abro tarjeta — decime cuál preferís."

Eso te deja parado como alguien que conoce los límites de su propio trabajo, que es más creíble que tener respuesta para todo.

---

## E. Los tres archivos que tenés que tener abiertos

| Para hablar de | Abrí |
|---|---|
| Cualquier "¿por qué así?" del Outbox | `docs/adr/ejemplo-paridad-servicio-hermano.md` |
| Cualquier "¿por qué así?" del logging | `docs/adr/ejemplo-alcance-logging.md` |
| "¿Cómo se despliega esto?" | `docs/guias/checklist-despliegue-outbox-api-core.md` |

---

## F. Mapa de campos (para cuando te preguntan "¿y este campo qué hace?")

### Lo primero: 6 campos NO son tuyos

Toda entidad hereda de `BaseDomainModel`, así que estos 6 aparecen en **todas** las tablas y no los escribiste vos:

| Campo | Qué es |
|---|---|
| `Id` | PK, `Guid` |
| `UsuarioRegistro` / `FechaRegistro` | Quién y cuándo creó la fila |
| `UsuarioModificacion` / `FechaModificacion` | Quién y cuándo la modificó |
| `EsActivo` | Borrado lógico — nada se borra físico |

Los llena solo el interceptor de auditoría (`AuditableEntitySaveChangesInterceptor`), tomando el usuario del JWT. Si te preguntan por uno de estos, la respuesta es "es auditoría estándar del `BaseDomainModel`, la llena el interceptor".

**Eso ya te cubre 6 de las 17 columnas de `RequestResponseLog`.**

### `RequestResponseLog` — los 11 campos propios

| Campo | Tipo | Qué guarda |
|---|---|---|
| `Timestamp` | `DateTime` | Cuándo ocurrió el fallo (UTC) |
| `RequestMethod` | `string` | GET, POST... |
| `RequestUrl` | `string` | Entrante: el endpoint de api-core. Saliente: la URL del servicio hermano |
| `ResponseStatus` | `int?` | El status HTTP. **`NULL` = no hubo respuesta** (timeout, DNS, conexión rechazada) |
| `ElapsedTime` | `TimeSpan` | Cuánto tardó antes de fallar |
| `UserAgent` | `string?` | Quién llamó |
| `CorrelationId` | `string` | El `TraceIdentifier` de ASP.NET — para hilar varias filas de la misma request |
| `RequestHeaders` | `string?` | JSON de headers. **Entrante: sin `Authorization`/`Cookie`. Saliente: completos** |
| `RequestBody` | `string?` | **Siempre `NULL`.** Existe solo por paridad de esquema con api-delivery (ADR-0016) |
| `ResponseHeaders` | `string?` | JSON de headers de la respuesta fallida |
| `ResponseBody` | `string?` | **El campo que importa.** Entrante: cadena de `InnerException` hasta 5 niveles + stack. Saliente: el body de error del hermano, o el tipo+mensaje de la excepción |

Todos los `string` se truncan a **32.768 caracteres** con un sufijo `...[truncado, original N chars]`.

### `OutboxMessage` — los 11 campos propios

| Campo | Qué guarda |
|---|---|
| `OccurredOnUtc` | Cuándo se generó el evento de dominio |
| `Type` | Nombre del tipo del evento (con qué handler se despacha) |
| `Content` | El evento serializado en JSON |
| `Status` | `int` 1..5 — ver la tabla de A6 |
| `IsProcess` | Bandera legada previa a `Status`; el `Status` manda |
| `ProcessedOnUtc` | Cuándo terminó OK. **Se limpia al reclamar para reejecución manual** |
| `Error` / `LastError` | `Error` es el fallo permanente; `LastError` el del último intento |
| `RetryCount` | Intentos consumidos |
| `NextRetryOnUtc` | Cuándo vuelve a ser elegible (lo calcula el backoff) |
| `LastAttemptOnUtc` | Cuándo se intentó por última vez — es lo que detecta los zombis |

### `OutboxRetryPolicy` — los 7 campos propios

| Campo | Qué controla |
|---|---|
| `EventType` | A qué tipo de evento aplica. `"DEFAULT"` es el comodín |
| `MaxRetries` | Cuántos reintentos antes de `DeadLetter` |
| `InitialDelaySeconds` | Espera base del primer reintento |
| `Strategy` | `Exponential` o fijo |
| `MaxDelaySeconds` | Techo de la espera |
| `ZombiRecoveryMinutes` | Minutos en `Processing` para considerarlo zombi |
| `RecuperarZombisComoRetry` | Si el zombi vuelve a la cola (`true`) o va directo a `DeadLetter` (`false`) |

**Detalle que te pueden marcar como bug y no lo es:** en la política de mensajería, `InitialDelaySeconds == MaxDelaySeconds == 30`, así que el jitter siempre queda recortado por el techo y el backoff da 30s fijo. Es intencional y está comentado en `CalcularBackoffSegundos`.

---

## G. Cómo responder cuando te preguntan un detalle que no tenés en la cabeza

Nadie sabe todos los campos de memoria — tampoco quien escribe el código a mano. Lo que se evalúa no es tu memoria, es si **el sistema es explicable y vos lo controlás**.

**El movimiento correcto, en este orden:**

1. **Ubicalo en voz alta.** "Ese campo está en `RequestResponseLog`, que es la entidad nueva del PR — dejame abrirla." Eso ya demuestra que sabés dónde vive todo, que es lo que realmente importa.
2. **Abrí el archivo y leelo.** Buscar delante de todos no es debilidad; es lo que hace cualquiera con un repo de este tamaño.
3. **Contestá con la razón, no solo con el tipo.** No "es un `int?`", sino "es `int?` porque cuando la llamada revienta por timeout no hay status que guardar, y ese `NULL` es justamente la señal de que no hubo respuesta".

**Lo único que no podés hacer es inventar.** Un "no me acuerdo, lo miro" cuesta cinco segundos; una respuesta inventada que después se cae te cuesta la credibilidad de todo el PR.

**Lo que sí conviene tener de memoria (es corto):**

- Las 6 capas y qué hace cada una → está en la página 3 · Componentes (C3) de [`contexto-negocio/diagramas/arquitectura-c4-api-core/`](../../contexto-negocio/diagramas/arquitectura-c4-api-core/).
- Que api-core tiene **un solo `DbContext`** (`CoreDbContext`) y por qué: es agregador/BFF, y desde el 2026-08-21 consume los servicios de entidades y acuerdos por HTTP, no leyendo sus bases. Tuvo tres hasta ese día; el test de arquitectura `DbContextEncapsulationTests` fija el estado actual. *(Corregido 2026-09-11: decía "3 `DbContext`".)*
- Los 5 estados del Outbox con su número.
- Los 5 riesgos conocidos (sección D).
- Por qué cada decisión rara → los ADR.

Todo lo demás se busca.

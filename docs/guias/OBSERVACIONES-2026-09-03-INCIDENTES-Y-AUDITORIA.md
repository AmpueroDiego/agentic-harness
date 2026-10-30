---
tipo: bitacora
fecha: 2026-09-03
tags: [bitacora, incidentes, api-core, api-auth, api-delivery, auth, m2m, seguridad]
---

# Bitácora 2026-09-03 — Incidentes de autenticación y auditoría del ecosistema

> Ejemplo histórico anonimizado: los estados y las mediciones describen aquella sesión; no afirman el estado de una instalación actual.

Sesión larga. Se cerró el diagnóstico del 502 de dev, apareció un incidente nuevo en `api-auth`, y una auditoría con Fable 5.1 dejó hallazgos que tocan el PR #21.

**Estado al cerrar:** backend local apagado. `api-core` en dev **sigue roto** para todo lo que dependa de un hermano.

---

## 1. El 502 de dev — causa raíz confirmada

### Qué pasa

`api-core` en Azure dev no puede autenticarse contra `api-auth`. Sin token de sistema no resuelve `URL_API_PEOPLE` ni `URL_API_CONTRACTS`, lanza `InvalidOperationException`, y el `ExceptionMiddleware` responde **502** en todo endpoint que salga a un hermano.

### La evidencia

```
POST <url-servicio>/api/Auth/Login
→ HTTP 400 {"Details":"Credenciales son incorrectas","Message":"NotFoundException"}
→ en ~22-47 ms, cada 30 segundos, 425 veces entre 20:04 y 23:57 UTC
```

**El dato que lo prueba: la latencia.** `api-auth` valida con BCrypt (work factor 11), que tarda cientos de milisegundos. Un login real medido hoy tardó **1062 ms**; el arranque del backend local, **909 ms**. Los fallos de dev promedian **40 ms**. BCrypt nunca se ejecuta → **el password llega vacío**, no incorrecto.

### Por qué local sí y Azure no

El `Host/appsettings.json` versionado trae `AdminSettings.Password: ""`. Ese valor lo completa:

| Ambiente | Fuente | Resultado |
|---|---|---|
| Local | user-secrets (`%APPDATA%\Microsoft\UserSecrets\61f0fa25-…`) | ✅ password real |
| Azure dev | Application Settings del App Service | ❌ no lo aportan |

Los user-secrets **nunca se despliegan** — no están en git, no van en `dotnet publish`. La contraparte en Azure son las Application Settings, y esa carga nunca se hizo.

> **Corrección respecto de lo que se pensó al principio:** el commit `<commit>` (2026-08-27) que dejó el password en `""` **no causó esto**. Antes decía `REPLACE_ME`, y `EsValorConfiguradoValido` (`ApiAuthService.cs:128`) trata `REPLACE_ME` igual que vacío. **Dev probablemente nunca pudo autenticarse M2M.** No es una regresión, es una configuración que nunca se completó.

### Verificado y descartado

- ✅ **La credencial es válida.** `<identidad-servicio>@<dominio>` + su password + `IdAplicacion 5E425394-…` → **200** contra dev.
- ✅ **La aplicación existe.** `[APLICACION].[Aplicacion]` tiene `API_CORE`, activa, registrada 2026-08-19 16:25.
- ✅ **Las Application Settings sí se leen.** `ObtenerUrlApiAuth()` lanza si `Settings:ApiAuth` está vacío, y dev llega a la URL correcta → esa clave viene de Azure y .NET la lee bien.
- ✅ **Un solo App Service.** El CD despliega a `<app-service-api-core>` (variable `AZURE_WEBAPP_NAME`); el hostname corto `<url-api-core-corta>` no responde, el bueno es `<url-api-core>`.
- ❌ **No es el Email ni el IdAplicacion.** Local usa exactamente los mismos y funciona.

### Pendiente

El equipo afirma que el password está cargado. Los datos dicen que no le llega al proceso. Lo zanja **Kudu**:

```
<url-servicio>
→ Debug console → Bash → printenv | grep -i adminsettings
```

Muestra las variables **como las ve el proceso**. Causas típicas de que se vea en el portal pero no llegue:

1. No se apretó **Save** (la fila aparece en la grilla sin aplicarse).
2. Cargada en **Connection strings** en vez de **Application settings** (queda con prefijo `CUSTOMCONNSTR_`).
3. Nombre con `:` en vez de `__` (en Linux .NET no lo ve).
4. Marcada como *deployment slot setting*, o en un slot que no sirve.

Alternativa barata: **reiniciar el App Service** (Overview → Restart) descarta config vieja en memoria.

**Termómetro:** si dejan de aparecer filas cada 30 s en `[SERVICIO].[RequestResponseLog]` con `RequestUrl LIKE '%Auth/Login%'`, quedó resuelto. Los éxitos no se loguean, por diseño (ADR-0016).

### Claves a cargar

| Application Setting | Valor |
|---|---|
| `Settings__ApiAuth` | `<url-servicio>` (ya está) |
| `AdminSettings__Email` | `<identidad-servicio>@<dominio>` |
| `AdminSettings__Password` | ← **el que falta** |
| `AdminSettings__IdAplicacion` | `<application-id>` |

---

## 2. Incidente en `api-auth` (cerrado solo)

Entre ~22:00 y ~23:20 UTC, `api-auth` de dev devolvió **500 en ~6 s a todo login exitoso**, mientras las credenciales inválidas seguían dando 400 al instante. Es decir: **fallaba después de autenticar**, en el tramo de generar token / registrar sesión.

- Probado con **2 cuentas** y **3 `idAplicacion`** distintos (incluidos `RefreshTokenMode` 0 y 1): fallaba en todos. No era específico de cuenta ni de aplicación.
- **Afectó a todo el ecosistema.** El `api-core` local también cayó — quedó registrado en su log local con 500 a partir de las 23:14, cuando se le venció el caché de 50 minutos del token.
- Se recuperó sin intervención.

### Hipótesis (no probada)

La base `Security` acumula tablas sin retención:

| Tabla | Filas | Tamaño | Estadísticas desde |
|---|---|---|---|
| `USUARIO.RefreshTokens` | 22,562,449 | **7.1 GB** | 2026-08-03 |
| `SERVICIO.RequestResponseLog` | 394,158 | **4.4 GB** | **2024**-07-31 |

`RefreshTokens` tiene **6 índices**, cuatro de ellos con **cero lecturas** pero mantenidos en cada INSERT. Cada login exitoso escribe ahí. La purga existe pero es manual y borra máximo 100K filas por llamada (`LimpiarRefreshTokenCommandHandler.cs:15-16`) — harían falta ~225 llamadas.

`analyze_database_size` devolvió *arithmetic overflow*, señal de que la base es muy grande.

**Confirmarlo requiere** Query Store / App Insights de `api-auth` entre 22:00 y 23:20 UTC. No es un problema de api-core, pero conviene reportarlo: va a volver a pasar.

### Consultas útiles para quien administre esa base

```sql
-- ¿Es basura acumulada?
SELECT COUNT(*) AS Filas, SUM(CASE WHEN ExpiresAtUtc < GETUTCDATE() THEN 1 ELSE 0 END) AS YaVencidos,
       SUM(CASE WHEN RevokedAtUtc IS NOT NULL THEN 1 ELSE 0 END) AS Revocados
FROM [USUARIO].[RefreshTokens];

-- ¿La base toca su límite?
SELECT TOP 20 end_time, avg_cpu_percent, avg_data_io_percent, avg_log_write_percent
FROM sys.dm_db_resource_stats ORDER BY end_time DESC;
```

---

## 3. Auditoría Fable 5.1 — hallazgos que tocan el PR #21

### P1 — resolver antes de la revisión

**H1. `DatosDisponible` nunca puede ser `false`** *(verificado leyendo el código)*

`ApiDeliveryService` **nunca lanza**: tiene `catch (Exception)` que devuelve lista vacía (`ApiDeliveryService.cs:23-38`) y ante `!response.IsSuccess` también (línea 52). El `catch` del handler que pone `datosDisponible = false` (`ObtenerResumenEntidadQueryHandler.cs:41-53`) es **código inalcanzable**.

Es la respuesta que se dio a un comentario de revisión del PR #19. Si Delivery se cae, el flag dice `true`. Sin tests: `grep DatosDisponible` en `api-core.Tests` da cero.

**Fix:** que `ApiDeliveryService` devuelva éxito/fallo (o lance) y el handler distinga.

**H2 + H9. El log de salientes guarda un token con acceso a toda la bóveda de secretos** *(verificado)*

`ClienteService.cs:62` pone el `Bearer` en `DefaultRequestHeaders`; .NET lo mergea al request antes del `DelegatingHandler`; `RequestResponseLoggingHandler.cs:183-215` serializa los headers completos. El `X-Api-Key` de PROVEEDOR viaja igual. El `ExceptionMiddleware` sí los excluye (líneas 33-34) — la asimetría es evidente.

Estaba documentado como riesgo aceptado en ADR-0016 §3 por paridad con `api-delivery`. **Lo que cambia la evaluación:** la cuenta `<identidad-servicio>@<dominio>` tiene el permiso `ServiceManage`, y `SERVICIO.Configuracion` de Security guarda claves de pasarela de pagos, contraseñas de servicios externos, tokens de SMS y credenciales de firma electrónica. Ese token puede leer cualquiera de esos valores, y queda en texto plano en una tabla sin retención.

**Fix:** reusar en el handler de salida el mismo `HashSet` de headers excluidos del middleware. ~5 líneas + test (el actual solo verifica el password, no el `Bearer` ni el `X-Api-Key`).

### P2 — deuda, no bloquea

| # | Hallazgo | Ubicación |
|---|---|---|
| H3 | Fallo de `api-people` → **404 "no existe"**; de `api-contracts` → **total 0**. Datos falsos al usuario. Viola la regla 3 de `CLAUDE.md` | `ApiPeopleService.cs:40`, `ApiContractsService.cs:43,55,68` |
| H4 | Sin lock al renovar el token: N requests concurrentes al minuto 50 = N logins simultáneos, cada uno escribiendo en `RefreshTokens` y `Sesion`. Mismo patrón en los 4 repos | `ApiAuthService.cs:34-56` (servicio `Scoped`) |
| H5 | Timeout único de 60 s para todo. vista de detalle hace una llamada por entidad → 5 entidades con `api-contracts` colgado = **~6 minutos** de request. Sin Polly ni resilience | `ClienteService.cs:58`, `ObtenerResumenEntidadQueryHandler.cs:111` |
| H6 | El "fallback a memoria" de Redis solo existe **al arrancar**. Si Redis se cae en caliente → 500. ADR-0012 promete algo que el código no hace. Hoy dev no usa Redis, `api-delivery` sí | `ServicesServiceRegistration.cs:20-31` |
| H8 | `RequestResponseLog` de api-core: 1.4 KB/fila, ~4 MB/día en el peor caso. **No urgente por tamaño, sí por diseño** — PK sobre GUID aleatorio, todo `nvarchar(max)`, sin índice en `Timestamp`. Cualquier purga futura hará table scan | migración `20260902234452` |
| H10 | `ExceptionMiddleware` mapea **toda** `InvalidOperationException` a 502 "servicio dependiente", incluidas las de dominio. Diagnóstico engañoso | `ExceptionMiddleware.cs:88-93` |
| H11 | `AdminSettings` no se valida al arranque; `Jwt` sí (`JwtOptionsValidator`). Con un validador equivalente, el incidente 1 habría sido un fallo de arranque explícito y no 425 logins fallidos en silencio | — |
| H12 | El caché de 50 min es ciego a la expiración real del token — nadie lee `expires`. Si el token durara menos, api-core serviría tokens vencidos | `ApiAuthService.cs:56` |

### Sobre el Outbox — tranquilizador

Si `api-auth` cae más de 30 minutos (el caché de config), el job se saltea cada ciclo con `LogWarning`, **pero no se pierde nada**: los mensajes quedan `Pending`/`ScheduledForRetry`. Al volver drena a `TOP (20)` cada 30 s = 40/min. También se pausa la recuperación de zombis mientras dure.

Estado actual en `Core`: 1 mensaje en `DeadLetter` (2026-09-02), 0 pendientes.

---

## 4. Hallazgo arquitectónico — `api-core` no hace M2M real

### Los cuatro repos se autentican como personas

| Repo | Endpoint | `ApiAuthService` escrito |
|---|---|---|
| api-people | `/api/Auth/Login` | 2024-06-24 |
| api-contracts | `/api/Auth/Login` | 2025-04-28 |
| api-delivery | `/api/Auth/Login` | 2025-10-24 |
| **El módulo M2M llegó** | | **2026-03** |
| api-core | `/api/Auth/Login` | 2026-08-15 |

**Tres de los cuatro se escribieron antes de que M2M existiera.** No tenían alternativa. Después llegó, `api-legacy` lo adoptó (2.343 emisiones en `TokenAudit`), y nadie migró los viejos. api-core copió el patrón de sus hermanos — que es lo que manda `CLAUDE.md` — y ese patrón ya estaba desactualizado.

### La diferencia concreta

| | `/api/Auth/Login` | `/api/Auth/Token` |
|---|---|---|
| Identidad | fila en `USUARIO.Usuario` con `PasswordHash` BCrypt | fila en `M2M.Client` con `ClientSecret` |
| Formato | JSON | form-urlencoded |
| **Escribe en** | **`RefreshTokens` + `Sesion`** | **solo `TokenAudit`** *(verificado en `ClientCredentialsTokenService.cs:106-109,159-172`)* |
| Secreto | password del usuario | revocable, con expiración |
| Duración | 8 h | 60 min (`M2MTokenOptions`) |

**El punto:** el incidente de anoche fue en el tramo del `Login` que escribe en `RefreshTokens`/`Sesion`. **M2M no pasa por ahí.** Los cuatro servicios cayeron juntos porque comparten ese camino.

### Qué costaría migrar (estimado 1-2 días + permisos de admin)

Hoy **no existe nada** de M2M para api-core — ni Client, ni secret, ni scopes, ni código. Los 3 clientes registrados son `api-legacy`, `legacy-dispatcher` y `api-payments`.

Alta necesaria en `api-auth`:
- `M2M.Client` con `ClientId: api-core` + `ClientSecret` (se muestra **una sola vez**).
- `ClientResourceAccess` contra la audiencia `api-auth` + scope `read:configuration`.
- **Crear los scopes `read:people` y `read:contracts`** — hoy solo existen `write:people`/`write:contracts`, y el emisor exige al menos un scope concedido.
- Para Delivery: no existe la `ApiResource`, y `api-delivery` valida una sola audiencia. Segunda fase.

Cambios en api-core:
- `IClienteService`: agregar `PostAsyncForm` (hoy solo JSON).
- `ObtenerTokenSistema(audience)`: un token por audiencia, TTL derivado de `expires_in` (cierra H12), y el lock anti-estampida (cierra H4).
- `ObtenerValuePorKey` apunta a `/api/integration/service/configuration` — el endpoint actual **rechaza tokens M2M** (`PermissionAuthorizationHandler.cs:11-12` exige `TokenSubjectType.User`).
- `appsettings`: `AdminSettings` → `M2M:{ClientId, ClientSecret}`.

**Qué se gana:** cero escrituras en `RefreshTokens`/`Sesion`; auditoría con IP y scopes; secreto revocable sin tocar `USUARIO.Usuario`; mínimo privilegio real (`read:configuration` en vez de `ServiceManage`, que hoy abre toda la bóveda de H9).

**Va como PR y ADR aparte, no dentro del #21.**

---

## 5. Hallazgos de seguridad (fuera del alcance del PR)

**Credenciales SQL en el historial de git de `api-core`.** Entre el **2026-08-17** (`<commit>`) y el **2026-08-26** (`<commit>`), el `Host/appsettings.json` versionado tuvo usuario y password reales de Azure SQL para `PeopleDb` y `CoreDb` (`ContractsDb` era `REPLACE_ME`). Nueve días. Están pusheados en `origin/develop` y varias ramas de feature. Repo privado, servidor dev.
→ **Rotar el usuario SQL de dev.** Reescribir el historial es opcional y no sirve si alguien ya clonó.
→ `AdminSettings:Password` **nunca** tuvo valor real en el repo: siempre `REPLACE_ME`, después `""`. Ese campo está limpio.

**`Jwt:SecretKey` real commiteado en `api-delivery`.** `api-delivery/Host/appsettings.json` tiene un valor real de 36 caracteres desde el **2026-05-20**, presente en `origin/main`. Con `Issuer: <emisor>` y `Audience: <audiencia>` — los mismos que usa api-core, o sea probablemente la clave de firma compartida del ecosistema. Repo privado.
→ No es del PR de api-core. Avisar al dueño de `api-delivery`. Rotarla obliga a coordinar los cuatro servicios.

**`api-contracts` usa la identidad de api-core.** Sus user-secrets locales tienen `AdminSettings:Email = <identidad-servicio>@<dominio>` e `IdAplicacion 5E425394-…`. Viola la regla de identidad propia de `CLAUDE.md` (al menos en local).

**Credenciales expuestas en la sesión de chat de hoy** (M2M y agente de prueba). Ya estaban además en `docs/pruebas/README.md` y `web-app/docs/CREDENCIALES-DEV.md`, ambos marcados como no comiteables. Rotar cuando dev vuelva a andar.

---

## 6. Correcciones a documentación existente

- **`CLAUDE.md` está desactualizado**: la sección "api-core es multi-DbContext a propósito" describe el estado previo al **2026-08-21**. El commit `<commit>` eliminó `ApplicationDbContext` y `ContractsDbContext`; hoy hay **un solo `CoreDbContext`**, y un test de arquitectura (`DbContextEncapsulationTests`) lo fija. La lección sobre `ApplyConfigurationsFromAssembly` sigue siendo válida, el motivo original ya no existe. *(Resuelto 2026-09-11: corregido en `CLAUDE.md`, `AGENTS.md`, `README.md` y `coder.md`. El motivo vigente de la regla: en el ensamblado quedan configuraciones de Contracts sin registrar.)*
- **`contexto-negocio/modelo-bd-crm.md`** tenía un `CORE_OUTBOX_MESSAGE` con esquema equivocado (es `SERVICIO`) y 6 columnas de 12. **Corregido hoy**, más el esquema `SERVICIO` completo.
- **`contexto-negocio/inventario-servicios-acmeorg.md`**: agregado el worker de Outbox, la bitácora de fallos, el webhook de PROVEEDOR como entrada, y corregido lo del `DbContext`.
- **La `Aplicacion` de dev se llama `API_CORE`**, no `ApiCore` como dicen varios docs. Irrelevante para el login.
- **La sección `Outbox: {IntervalInSeconds, BatchSize}` del `appsettings.json` no la lee nadie** — ni en api-core ni en api-delivery (que lee `TasksToExecute`, sección que tampoco existe en su JSON y cae a los defaults del `??`). En api-core los valores reales están cableados: **30 s** (`PersistenceServiceRegistration.cs:39`) y **`TOP (20)`** (`ProcessOutboxMessagesJob.cs:228`).

---

## 7. Para mañana — orden sugerido

1. **Kudu** en `<app-service-api-core>` → `printenv | grep -i adminsettings`. Cinco minutos y cierra el 502.
2. Si no aparece: cargar `AdminSettings__Password` en **Application settings** (doble guion bajo) y **Save**. Verificar en la tabla de logs que dejen de aparecer filas cada 30 s.
3. **Fix H2** (headers excluidos en el handler de salida) — es el que un revisor puede marcar como problema de seguridad. Vía `/orquestar`.
4. **Fix H1** (`DatosDisponible`) — promesa del PR #19 que no funciona.
5. Repasar `PREPARACION-DEFENSA-CODE-REVIEW.md`, especialmente la sección D (los 5 puntos débiles) y la F (mapa de campos).
6. Reportar a quien administre `api-auth`: el incidente del 500 y las tablas sin retención.
7. Anotar como tarjetas: rotación de credenciales SQL, `Jwt:SecretKey` de Delivery, migración a M2M.

## 8. Estado al cerrar

| | Estado |
|---|---|
| `api-core` local | apagado (andaba todo verde) |
| `api-auth` dev | recuperado |
| `api-core` dev | ⚠️ 502 en lo que depende de hermanos |
| `SERVICIO.RequestResponseLog` en Core | creada, funcionando, 425+ filas |
| Suite Apidog | lista — usar la **Cuenta de Agente de Prueba**, no la M2M |

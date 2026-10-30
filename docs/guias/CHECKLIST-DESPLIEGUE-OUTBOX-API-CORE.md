---
tipo: guia
fecha: 2026-10-30
tags: [harness, guia]
---

# Checklist de despliegue — Outbox con reintentos (api-core)

> 🏠 **Navegación:** [[Home|Home (Dashboard)]] · [[docs/guias/PLAYBOOK-ANTI-REGRESIONES-Y-LECCIONES-APRENDIDAS|Playbook Anti-Regresiones]] · [[docs/adr/0006-eventos-de-dominio-y-consumidor-outbox|ADR-0006 Eventos de dominio y Outbox]] · [[contexto-negocio/api-delivery-arquitectura|Outbox original en api-delivery]] · [[contexto-negocio/inventario-servicios-acmeorg|Inventario de Servicios]]

**Repo:** `api-core` · **Rama de origen:** `feature/outbox-reintentos` (PR #20) · **ADRs relacionados:** [`docs/adr/0013-outbox-reintentos-quartz.md`](../../docs/adr/0013-outbox-reintentos-quartz.md), `0014-alineacion-outbox-dapper-paridad-edb.md`, `0015-paridad-literal-edb-mantenibilidad-vs-practicidad.md`

`ProcessOutboxMessagesJob` (Quartz, corre cada 30s, registrado en `Persistence/PersistenceServiceRegistration.cs`) no hace nada útil por defecto en un ambiente nuevo — necesita 3 piezas de configuración externas al código, ninguna cubierta por una migración automática end-to-end. Este checklist nació de verificar en vivo, contra la BD real de dev, que las 3 faltaban simultáneamente (2026-09-02).

## 1. Migraciones EF Core aplicadas

> **Ninguna API del ecosistema aplica migraciones al arrancar.** Verificado el 2026-09-03 en los 4 repos (`api-core`, `api-contracts`, `api-people`, `api-delivery`): no hay un solo `Database.Migrate()`/`MigrateAsync()` fuera de los fixtures de test. Las migraciones **siempre** se aplican desde afuera — `dotnet ef database update` o un script SQL. No existe un ambiente donde "se apliquen solas".

El job depende de tablas/columnas que llegaron en 3 migraciones consecutivas — si el ambiente no las tiene, el job revienta en tiempo de ejecución al primer intento de leer `OutboxRetryPolicy` o las columnas nuevas de `OutboxMessage`:

- `20260901162313_AgregarOutboxReintentos` (crea `SERVICIO.OutboxRetryPolicy` + columnas de reintento en `OutboxMessage`)
- `20260902151204_AgregarCheckConstraintStatusOutboxMessage`
- `20260902154111_ReducirMaxLengthTypeOutboxMessage`

Verificar qué falta contra el ambiente real:
```sql
SELECT MigrationId FROM [__EFMigrationsHistory] ORDER BY MigrationId DESC;
```

Generar el script idempotente real (no escribir el DDL a mano) desde `api-core/`:
```bash
dotnet ef migrations script <ULTIMA_MIGRACION_YA_APLICADA> --project Persistence --startup-project Host --idempotent -o migracion-outbox-reintentos.sql
```
`--idempotent` hace que el script se salte lo que ya esté aplicado, seguro de re-correr.

⚠️ **El script de migraciones no trae datos semilla** — confirmado vacío de `INSERT` salvo los de `__EFMigrationsHistory`. El seed del punto 2 es obligatorio aparte.

## 2. Seed de `SERVICIO.OutboxRetryPolicy`

Sin al menos una policy `DEFAULT` sembrada, `OutboxRetryPolicyResolver` cae a un fallback defensivo en memoria con **`MaxRetries = 0`** (`Persistence/Repositories/OutboxRetryPolicyResolver.cs:24-39`) — el mensaje nunca reintenta, va directo a `DeadLetter` en el primer fallo. El fallback evita un crash, pero no sirve para producción real.

```sql
IF NOT EXISTS (SELECT 1 FROM [SERVICIO].[OutboxRetryPolicy] WHERE [EventType] = 'DEFAULT')
INSERT INTO [SERVICIO].[OutboxRetryPolicy]
    ([Id], [EventType], [MaxRetries], [InitialDelaySeconds], [Strategy], [MaxDelaySeconds], [ZombiRecoveryMinutes], [RecuperarZombisComoRetry], [EsActivo], [UsuarioRegistro], [FechaRegistro])
VALUES
    (NEWID(), 'DEFAULT', 5, 30, 2 /* Exponential */, 3600, 30, 0, 1, '<usuario>', SYSUTCDATETIME());

IF NOT EXISTS (SELECT 1 FROM [SERVICIO].[OutboxRetryPolicy] WHERE [EventType] = 'MensajeNotificacionFallidoDomainEvent')
INSERT INTO [SERVICIO].[OutboxRetryPolicy]
    ([Id], [EventType], [MaxRetries], [InitialDelaySeconds], [Strategy], [MaxDelaySeconds], [ZombiRecoveryMinutes], [RecuperarZombisComoRetry], [EsActivo], [UsuarioRegistro], [FechaRegistro])
VALUES
    (NEWID(), 'MensajeNotificacionFallidoDomainEvent', 5, 30, 1 /* Fixed */, 30, 30, 0, 1, '<usuario>', SYSUTCDATETIME());
```

`Strategy`: `1 = Fixed`, `2 = Exponential` (`Domain/Enums/Core/BackoffStrategyEnum.cs`). `EventType` de eventos específicos debe matchear literal el `nameof()` registrado en `Application/Common/OutboxEventTypeRegistry.cs` (hoy solo `MensajeNotificacionFallidoDomainEvent`) — cualquier otro nombre cae al `DEFAULT` silenciosamente, no es un error.

Índice único en `EventType` (`OutboxRetryPolicyConfiguration.cs`) — el `IF NOT EXISTS` evita el conflicto en reintentos del script.

> 📄 **Script listo para ejecutar:** [`scripts/seed-outbox-retry-policy.sql`](../../scripts/seed-outbox-retry-policy.sql) — mismos valores que el SQL de arriba, más guard de base, TRY/CATCH sobre el índice único y resumen final. Conectarse **directamente a la base `Core`** (Azure SQL no soporta `USE`).

⚠️ **No sembrar `DEFAULT` con `MaxRetries = 0`.** Esos son exactamente los valores del fallback defensivo en memoria (`OutboxRetryPolicyResolver.cs:28-39`), así que la fila no cambiaría el comportamiento en nada — solo silenciaría el warning del log. La versión original de `seed-outbox-retry-policy.sql` tenía justamente ese defecto, corregido el 2026-09-03. (El fixture `api-core.IntegrationTests/DatabaseFixture.cs` sí usa `0` a propósito, para aislar el comportamiento de la policy específica en los tests — esa divergencia es deliberada.)

## 2-bis. Tabla `SERVICIO.RequestResponseLog` (observabilidad de errores)

Desde [`ADR-0016`](../../docs/adr/0016-alcance-request-response-logging-outbound-solo-error.md), `ExceptionMiddleware` persiste cada fallo con **el mismo `Id` que devuelve al cliente**, y `RequestResponseLoggingHandler` registra las llamadas salientes fallidas. Ambos escriben en `SERVICIO.RequestResponseLog`.

Si la tabla no existe, el `INSERT` falla y el `try/catch` de ambos escritores lo absorbe: **no se rompe nada, pero tampoco se registra nada** — un no-op silencioso que da la falsa impresión de que "no hubo errores".

La tabla la crea la migración `20260902234452_AgregarRequestResponseLog`. **Aplicarla con `dotnet ef database update`** — ese es el camino que corresponde, igual que con cualquier otra tabla.

*Alternativa solo si en ese ambiente no se puede correr EF (sin repo, sin .NET instalado, o restricción de red): [`scripts/crear-request-response-log.sql`](../../scripts/crear-request-response-log.sql) es la misma migración traducida a SQL, y registra el `MigrationId` en `__EFMigrationsHistory` para que EF no intente re-aplicarla. **No es un script de sembrado** — el sembrado de datos (punto 2) es otra cosa.*

Verificar:
```sql
SELECT COUNT(*) FROM [SERVICIO].[RequestResponseLog];
SELECT * FROM [__EFMigrationsHistory] WHERE MigrationId LIKE '%RequestResponseLog%';
```

## 3. Key de activación remota en `api-auth`

El job hace un gate check contra `api-auth` **antes de cualquier otra cosa** (`Persistence/Jobs/ProcessOutboxMessages/ProcessOutboxMessagesJob.cs:53-66`) — si la key no existe, está en `false`, o la llamada falla (red/credenciales), el job se salta el ciclo completo sin tocar ninguna fila.

Tabla real: `api-auth` → base `Security` → **`SERVICIO.Configuracion`** (`Id` uniqueidentifier, `Key`/`Value`/`Descripcion` nvarchar(max) NOT NULL, `EsActivo` bit NOT NULL — **sin unique constraint en `Key`**, cuidado con duplicados).

```sql
IF NOT EXISTS (SELECT 1 FROM [SERVICIO].[Configuracion] WHERE [Key] = 'API_CORE_JOB_OUTBOX_ACTIVADO')
INSERT INTO [SERVICIO].[Configuracion]
    ([Id], [Key], [Value], [Descripcion], [UsuarioRegistro], [FechaRegistro], [EsActivo])
VALUES
    (NEWID(), 'API_CORE_JOB_OUTBOX_ACTIVADO', 'true',
     'Interruptor remoto que activa/desactiva ProcessOutboxMessagesJob (reintentos de Outbox) en api-core.',
     '<usuario>', SYSUTCDATETIME(), 1);
```

Convención de nombre confirmada contra datos reales de la tabla: `API_ACCOUNTING_JOB_OUTBOX_ACTIVADO` y `API_LEGACY_JOB_OUTBOX_ACTIVADO` ya existen con `Value = "true"`, mismo patrón `API_<SERVICIO>_JOB_OUTBOX_ACTIVADO`.

⚠️ **Bug conocido en `api-delivery` — no replicar ese patrón:** su `ProcessOutboxMessagesJob.cs:57` y `TareaProgramadaJob.cs:32` consultan `API_LEGACY_JOB_OUTBOX_ACTIVADO` / `API_LEGACY_JOB_TAREASPROGRAMADAS_ACTIVADO` en vez de una key propia (`API_DELIVERY_...`) — así desde el commit original del archivo (`<commit>`, <fecha>), copiado sin renombrar al clonar la infraestructura de jobs desde api-legacy. Hoy funciona solo porque ambas keys de api-legacy están en `"true"`; apagar la key de api-legacy apagaría silenciosamente los 2 jobs de api-delivery también. Reportado al equipo, no corregido — verificar si sigue así antes de asumir que `api-delivery` es una referencia confiable para este patrón.

## 4. Credenciales de la aplicación contra `api-auth`

`ObtenerValuePorKey` necesita que el proceso pueda autenticarse como `<identidad-servicio>@<dominio>` (`IdAplicacion: <application-id>`, versionado en `Host/appsettings.json`; `AcmeOrg/CLAUDE.md` solo nombra el email). Si faltan, el gate check lanza excepción y el log dice `"Gate check de ProcessOutboxMessagesJob falló contra api-auth, se salta este ciclo."` — **este mensaje no significa que la key no exista**, significa que la llamada en sí falló (confirmado leyendo el `catch` de `ProcessOutboxMessagesJob.cs:62-66`).

- Local: `dotnet user-secrets` — `Settings:ApiAuth`, `AdminSettings:Email`, `AdminSettings:Password`, `AdminSettings:IdAplicacion`.
- Azure (Dev/QA/Prod): Application Settings del App Service — `Settings__ApiAuth`, `AdminSettings__Email`, `AdminSettings__Password`, `AdminSettings__IdAplicacion`.

Nunca en `appsettings.json` versionado (ver política de secretos en `AcmeOrg/CLAUDE.md`).

## 5. Verificación

1. Levantar el Host y confirmar en el log: `"ProcessOutboxMessagesJob ACTIVADO: SI"` (no el warning de gate check fallido).
2. Provocar un envío de Notificacion que PROVEEDOR **rechace explícitamente** (respuesta de error, no un timeout ni PROVEEDOR caído: un fallo de transporte deja el mensaje en `Enviando` y el reintento lo manda directo a `DeadLetter`) para que se registre un `MensajeNotificacionFallidoDomainEvent` en `SERVICIO.OutboxMessage`, y observar `RetryCount`/`NextRetryOnUtc` avanzar en ciclos de ~30s con `Status = 3` (`ScheduledForRetry`) (con la policy `Fixed` sembrada arriba). No existe un `Status` "fallido": los estados son `1 Pending`, `2 Processing`, `3 ScheduledForRetry`, `4 Processed`, `5 DeadLetter` (`Domain/Enums/Core/OutboxMessageStatusEnum.cs`). *(Corregido 2026-09-11: decía "con `Status` fallido".)*
3. Confirmar que `ConexionSql` del ambiente apunta a la misma BD donde se aplicaron los puntos 1-2 — si el Host corre contra una BD distinta a la que se verificó, todo lo anterior puede estar resuelto en un lugar y faltar en otro.

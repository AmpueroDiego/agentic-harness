# AcmeOrg — instrucciones generales

Aplica a cualquier sesión con `AcmeOrg/` como working directory, sin importar en qué repo hermano se trabaje. Cada repo puede tener además su propio `CLAUDE.md` con lo específico.

## Visión de dominio

*(Sección retirada en la versión pública: contenía las prioridades de producto y las reglas de negocio del cliente. Los agentes la leen antes de proponer un diseño; en tu adaptación, describe aquí en 3 puntos ordenados cómo debe pensar el equipo de agentes sobre tu dominio, y qué reglas NO debe inventar por iniciativa propia.)*

## Repos y rama base

Bloque de ejemplo — reemplázalo por tus repos. Los agentes asumen un BFF que agrega datos de servicios hermanos por HTTP, un IdP y un frontend.

| Repo | Rol | `CLAUDE.md` propio |
|---|---|---|
| `api-core` | BFF/agregador, .NET 10, un solo `DbContext` | sí |
| `api-contracts` | Servicio de acuerdos comerciales (solo lectura desde `api-core`) | no |
| `api-people` | Servicio de personas: datos de contacto, direcciones, teléfonos, emails | no |
| `api-auth` | IdP: emite los JWT y define roles/permisos | no |
| `api-delivery` | Servicio de logística y entregas | no |
| `web-app` | Frontend React/TypeScript | no |

**Todo apunta a `develop`, nunca a `main`.** El flujo real es `develop` → `qa` → `main`.

- Las ramas de trabajo se crean **desde `develop`**: `git checkout develop && git pull` antes de ramificar.
- Los PRs se abren **contra `develop`**. GitHub propone `main` por defecto en su banner — hay que cambiarlo a mano cada vez. Ya hubo PRs que aterrizaron directo en `main` saltándose el flujo.
- `refs/remotes/origin/HEAD` de cada repo debe apuntar a `develop` (`git remote set-head origin develop`). Si un diff automático sale desproporcionado (el skill `security-review` calcula el suyo contra `origin/HEAD`), sospecha de esto primero.
- El hook `git-guard.sh` bloquea `gh pr create` sin `--base develop`. El que corre es `~/.claude/hooks/git-guard.sh` (registrado a nivel de usuario); `.claude/hooks/git-guard.sh` es su copia versionada y se mantiene idéntica.

## Cero eliminaciones y consentimiento previo

- **NUNCA ELIMINAR NADA** sin instrucción explícita e inequívoca: ni tarjetas del tablero de tareas, comentarios, adjuntos, ramas remotas, código, tablas ni archivos de documentación.
- **Antes de cualquier mutación en el tablero de tareas** (mover de columna, editar descripciones, asignar miembros, adjuntar) o de cualquier acción destructiva en Git/BD, presenta la propuesta exacta con todos sus campos y espera aprobación expresa.

## Flujo de trabajo

- **Todo cambio de código pasa por `/orquestar`** (comando en `.claude/commands/`, agentes en `.claude/agents/`), no se edita directo en chat — incluso cambios chicos. Target por defecto `api-core`.
- **Trabajo en paralelo por olas: `/worktree`.** Una tarjeta = una rama = un worktree en `.worktrees/<repo>--<slug>` = una sesión abierta **en la raíz de AcmeOrg**, que corre `/orquestar --en .worktrees/<repo>--<slug> ...`. Antes del PR, `/worktree sincronizar` (merge de develop + build + tests sobre el código combinado). En ese modo no se sube la rama ni se abre PR hasta que el responsable del repo lo pida.
- **Cada pedido no trivial se registra en [`TASKS.md`](TASKS.md)** — fecha, repo(s), pedido, estado (🟡 Pendiente / 🔵 En curso / ✅ Hecho / ⏸️ Pausado / ❌ Descartado) y link al run doc o commit. La fila se agrega **al empezar**, no al terminar, para que quede constancia si la sesión se corta.
- **Entrega en el tablero de tareas y GitHub.** Lo que más se equivoca: el título de una tarjeta existente no se toca; el PR se vincula a la tarjeta por la integración nativa del tablero, sin comentarios redundantes; **la tarjeta pasa a la columna de revisión solo cuando el responsable del repo lo pide**, no al abrir el PR (desde 2026-09-19). **Toda operación sobre el tablero va por una herramienta determinista que simula antes de escribir**, nunca Python suelto contra la API. *(En el original esto era una skill sobre la API de Trello con los ids del tablero del cliente; se retiró de la versión pública.)*

## Playbook

> [!IMPORTANT]
> Antes de implementar o modificar código, consultar el playbook anti-regresiones del proyecto — catálogo de reglas de oro contra errores comunes, cada una nacida de una regresión real. Sin número de reglas acá: ya se desfasó una vez. *(El playbook original se retiró de la versión pública porque cada regla citaba código del cliente; en tu adaptación, mantén uno en `docs/guias/` y cítalo desde acá.)*

**Principios de diseño (desde el 2026-09-17):** KISS, YAGNI, DRY y SOLID, con los cinco síntomas que ya aparecieron acá (fat controller, Smart UI, validación solo del lado del cliente, cajón de sastre, modelo ajeno filtrado hacia adentro). **La regla que manda: si lo que vas a tocar ya está mal, se arregla primero y en un commit aparte; no se construye encima.** Lo que no entre en el alcance se reporta con `archivo:línea` y se registra en `TASKS.md` con su tarjeta.

De ahí, la que más cuesta cuando se olvida: **ninguna API auto-migra**. Una migración de EF Core no se aplica sola al desplegar; el fallo es silencioso.

## Base de datos — Azure SQL

Todas las bases viven en el mismo servidor lógico `<sql-host>` (dev, data mockeada), como bases separadas: `Contracts`, `People`, `Security` y la propia de api-core.

**Azure SQL Database no soporta queries cruzados entre bases con nombre de 3 partes**, aunque compartan servidor lógico — a diferencia de SQL Server on-prem o Managed Instance. Confirmado con error real: `SELECT ... FROM [Contracts].[dbo].[Agreement] c JOIN [People].[dbo].[Person] p ...` falla con `SQL Error [40515]`.

Si hay que dar una query manual que combine dos bases: siempre **dos queries separadas, correlacionadas a mano por `Id`**. El match por convención de Id (sin FK física entre las dos bases) funciona en la práctica para el patrón titular→cliente.

**`api-core` tiene un solo `DbContext`: `CoreDbContext`** *(verificado en `develop` el 2026-09-11)*. Tuvo tres hasta el 2026-08-21, cuando un commit pasó People y Contracts a HTTP y eliminó `PeopleDbContext` y `ContractsDbContext`; hoy api-core no lee esas bases directo, y el test de arquitectura `DbContextEncapsulationTests` fija ese estado.

La regla que nació en la época de los tres contextos sigue vigente, por otra razón: **nunca `ApplyConfigurationsFromAssembly` en `CoreDbContext`**. En `Persistence/Configuration/External/` quedaron configuraciones de entidades de otra base que ya nadie registra, dentro del mismo ensamblado; escanearlo las metería en el modelo propio y la siguiente migración intentaría crear esas tablas. Con tres contextos ya pasó lo mismo: el escaneo se llevó las configuraciones ajenas sin que nadie lo notara hasta generar una migración. Registrar cada configuración explícita por entidad.

## Secretos y configuración

- **Prohibido versionar cadenas de conexión o credenciales.** En todo `appsettings*.json` comiteado, las claves sensibles quedan en `""` o `"REPLACE_ME"` por convención (`ConexionSql`, `ConexionRedis`, `SecretKey`, `Password`, `ApiKey`, `WebhookSecret`, `Settings:ApiAuth`, `AdminSettings:Password`). `AdminSettings:Email` e `AdminSettings:IdAplicacion` sí van con valor a propósito: identifican al servicio, no son secretos. `appsettings.Development.json` va en el `.gitignore` de cada repo y nunca se comitea. En local: `dotnet user-secrets`; en Azure: Application Settings / Key Vault.
- **Fallback seguro ante placeholders:** `""` y `"REPLACE_ME"` son strings no nulos, así que `??` nunca alcanza el fallback. Trata vacío, solo-espacios y `"REPLACE_ME"` (case-insensitive) como ausente **antes** de evaluar el fallback. Patrón de referencia en el repo: `EsValorConfiguradoValido()`.
- **URLs de servicios hermanos: nunca estáticas.** Se resuelven en runtime vía `IApiAuthService.ObtenerValuePorKey("URL_API_PEOPLE" | "URL_API_CONTRACTS" | "URL_API_DELIVERY", true)`, y toda URL resuelta se limpia con `.Trim('"', ' ', '/')`.
- **Identidad propia por microservicio:** cada API se autentica ante `api-auth` con su propia identidad, nunca prestando credenciales de un hermano. `api-core` es `<identidad-servicio>@<dominio>`.
- **Revisor de secretos único: `.claude/hooks/revisar_secretos.py`** (desde 2026-09-17). Bloquea el commit si en el stage hay un `appsettings*.json` con valor real en clave sensible, un `.env`/`appsettings.Development.json`, o un Word/Excel/PowerPoint con claves o cadenas de conexión. Lo llaman el hook de Claude (`git-guard.sh`) y un `pre-commit` de git real, así protege también los commits desde VS Code o la terminal: la raíz usa `scripts/hooks/` (secretos + vault) y los repos hijos `scripts/hooks-repos/` (solo secretos, worktrees incluidos). **Instalado solo en `api-core`** por decisión del responsable del repo (2026-09-17); para otro hijo: `git -C <repo> config core.hooksPath <ruta absoluta a scripts/hooks-repos>`, y `sh scripts/instalar-hooks.sh` los configura todos. Límite conocido: en Excel, una clave y su valor en celdas separadas no se detectan. Tests: `python .claude/hooks/test_revisar_secretos.py`. Al cambiarlo, copiar también `revisar_secretos.py` y `check-appsettings.py` a `~/.claude/hooks/`, igual que `git-guard.sh`.

## Lectura de archivos grandes (shunt)

Dos hooks `PreToolUse` a nivel usuario (`~/.claude/settings.json`) bloquean leer un archivo de más de 350 líneas completo (`Read` sin `offset`/`limit`, o `cat`/`type` sin pipe) y redirigen a `bulk-read.sh`, que lo resume con `agy` (Antigravity CLI, Gemini) sin gastar el contexto de Claude — inspirado en [Portal by Spotify](https://engineering.atspotify.com/2026/9/portal-by-spotify-cut-my-claude-code-token-usage-by-90). `code-write.sh` genera archivos mecánicos acotados (spec + referencia) como motor adicional del reparto de coders de `/orquestar`, sin saltarse QA/adversary — también sirve, sin script nuevo, para un primer borrador de diagramas `.diagrama.json` y de ADRs. El patrón también cubre la **salida de comandos**, no solo archivos *(desde 2026-09-18)*: `gh-read-shunt.sh` lee resultados grandes de `gh` (lecturas únicamente — las mutaciones siguen directo, y `gh pr create`/`merge`/`close` nunca se delegan), porque los dos hooks de arriba solo interceptan `Read`/`cat`, nunca la salida en vivo de un subproceso. Detalle, variables de entorno y límites conocidos (el contenido no se puede embeber en `--print="..."` en Windows, por el límite de longitud de línea de comando): [`/shunt`](.claude/commands/shunt.md). Copias reales en `~/.claude/{hooks,scripts}/`, versionadas en `.claude/{hooks,scripts}/` — mismo criterio que `git-guard.sh`.

## Reglas permanentes de mensajería, persistencia y frontend

1. **Resolución de dependencias antes de side-effects externos.** Si un comando despacha mensajes (WhatsApp vía WAHA, correo vía SMTP) y debe asociarse a una entidad maestra (ej. `CustomerId`), la resolución y validación de esa entidad va **antes** del envío. Nunca disparar el efecto externo antes de garantizar que el registro no quedará huérfano.
2. **Identificadores de proveedores externos: `nvarchar(450)`**, nunca `nvarchar(100)`. Es el máximo compatible con índices únicos en SQL Server; menos trunca ids reales y puede colgar un poller en bucle infinito. Hay un hook que avisa (`check-maxlength.py`).
3. **Privacidad de SignalR:** los DTOs del broadcast global (grupo `Agentes`) son resúmenes livianos; nunca emitir `Contenido` ni datos de contacto completos ahí. El detalle va solo al grupo del cliente (`cliente-{CustomerId}`).
4. **Agregación sobre colecciones completas en frontend:** los agregados del cliente (saldos, máximos, alertas) se calculan con `.reduce()` y `Math.max()` sobre la colección completa — nunca `items[0]`. `[0]` solo vale como fallback explícito después de buscar por clave, jamás para agregar montos.
5. **Decodificación de JWT en el cliente:** nunca `atob` pelado sobre tokens con base64url (`-`, `_`) o claims con tildes/eñes. Normalizar a base64 con padding y decodificar con `TextDecoder("utf-8")`.
6. **Aislamiento de sesión en la SPA:** ningún estado de usuario (historiales, cachés, colas) sobrevive al logout en variables a nivel de módulo. Todo store en memoria se limpia con `clearAccessToken` o se filtra por el `userId` del JWT activo. Asume dos pestañas con usuarios distintos.

## Auditoría adversarial

Los **6 vectores de ataque** y las **10 heurísticas de resiliencia nivel producción** viven en [`.claude/agents/adversary.md`](.claude/agents/adversary.md), que es su único dueño — se cargan cuando corre el agente que las usa, no en cada sesión. No los copies acá: ya divergieron una vez (un archivo decía 8 sobre una lista de 10).

## Compatibilidad multiplataforma (macOS, Linux, Windows)

- **`app.UseHttpsRedirection()` siempre condicional** (`if (!app.Environment.IsDevelopment())`). En macOS, Safari/Chrome rechazan los SSL self-signed certs de .NET con `ERR_CERT_AUTHORITY_INVALID`, y Swagger UI y el frontend fallan con `TypeError: Failed to fetch`. *(**Estado real y deuda aceptada, 2026-09-07:** solo `api-core` cumple; los servicios hermanos lo llaman incondicional, y **el responsable del repo decidió explícitamente dejarlos así**. No lo propongas como bug nuevo ni lo corrijas de paso: confirma primero si la decisión sigue vigente. Consecuencia asumida: quien levante el stack desde una Mac verá Swagger y el frontend fallar con `TypeError: Failed to fetch`, que parece CORS y no lo es. Y si el `architect` compara contra los hermanos para verificar paridad, va a ver lo contrario de esta regla: **`api-core` es la referencia correcta acá, no los otros.**)*
- **CORS tolerante en Development:** si `Cors:AllowedOrigins` está vacío o en `"REPLACE_ME"`, activar `SetIsOriginAllowed(_ => true).AllowAnyHeader().AllowAnyMethod().AllowCredentials()` para que cualquier origen local (Vite) funcione sin fricción.
  - *(**Aviso, verificado en `develop` el 2026-09-11:** el código de `api-core` va más allá de la regla — usa `IsDevelopment() || allowedOrigins.Length == 0`, así que abre a cualquier origen con credenciales **en cualquier ambiente** si `Cors:AllowedOrigins` llega vacío, y el `appsettings.json` comiteado trae `[ "" ]`. En QA/Prod sin ese App Setting queda abierto.)*

## UTF-8 en la CLI de Windows

PowerShell 5.1 usa codificación OEM (`CP850`/`Windows-1252`): los emojis se vuelven `??`, los acentos `?` y los latinos caracteres de control.

- **Nunca** pasar textos largos con emojis o tildes por pipe o argumento directo a `gh pr create`/`gh pr edit` ni a la API del tablero. Escribir el cuerpo en un `.md` temporal en **UTF-8 sin BOM** y pasarlo con `--body-file`.
- En scripts `.ps1`: `[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)`.
- **Compilación limpia:** en Windows, si el Host corre en background (`dotnet run`), las DLLs quedan bloqueadas (`Could not copy Domain.dll... locked by: Host`). Detener el proceso antes de `dotnet build`.

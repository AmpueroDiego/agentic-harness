---
description: Crea, lista, sincroniza con develop y cierra worktrees de los repos hijos (api-core, web-app…) para trabajar varias tarjetas en paralelo, una sesión por worktree.
argument-hint: crear <repo> <feature|fix>/<slug> [--run NNNN] [--bd-docker [--seed]] | listar | sincronizar <repo>--<slug> [--seguido] | cerrar <repo>--<slug>
---

Acción pedida: $ARGUMENTS

**Para qué existe** *(2026-09-11)*: trabajar por olas — varias tarjetas a la vez, cada una en su rama y su carpeta — sin que una sesión pise a otra. La herramienta nativa de worktrees de Claude Code no sirve acá: crea worktrees de `AcmeOrg/` (agentic-harness, en `.claude/worktrees/`), no de los repos hijos.

**Reglas fijas:**
- Los worktrees viven en `AcmeOrg/.worktrees/<repo>--<slug>/`. El punto inicial lo esconde de Obsidian, y la palabra `worktrees` lo saca de `scripts/validar-vault.py` — sin eso el vault vería copias duplicadas de cada run doc.
- **La sesión de Claude se abre siempre en la raíz de `AcmeOrg/`**, nunca dentro del worktree: solo ahí cargan `CLAUDE.md`, los agentes, los hooks y la memoria. El worktree se trabaja como destino (`/orquestar --en .worktrees/<repo>--<slug> ...`).
- Repos válidos: `api-core`, `api-contracts`, `api-people`, `api-auth`, `api-delivery`, `web-app`.
- Todo `git` va con `git -C <ruta>`; nada de `cd` compuesto.
- **Ni este comando ni `/orquestar --en` suben ramas ni abren PRs** *(pedido del responsable del repo, 2026-09-11)*. Dejan la rama verificada y lista; el push y el PR contra `develop` se hacen solo cuando el responsable del repo los pide, rama por rama. No los ofrezcas al cerrar un paso.
- **Nada se borra sin aprobación expresa** (`CLAUDE.md`): ni ramas locales ni remotas, ni worktrees con trabajo, ni `--force`.
- Nunca leer ni mostrar el contenido de los archivos de configuración local que se copian — solo sus nombres.

## crear <repo> <feature|fix>/<slug> [--run NNNN] [--bd-docker [--seed]]

1. Valida que `<repo>` esté en la lista y que la rama siga la convención `feature/<slug>` o `fix/<slug>` (minúsculas y guiones).
2. `git -C <repo> fetch origin develop`. Si falla por credenciales, pídele al responsable del repo que lo corra él con `!` — no sigas con un `develop` viejo.
3. La rama no debe existir: `git -C <repo> rev-parse --verify --quiet refs/heads/<rama>` y `git -C <repo> ls-remote --heads origin <rama>`. Si existe en cualquiera de los dos, **para y pregunta**: ¿reusarla (`worktree add <ruta> <rama>`) o elegir otro nombre?
4. Crea el worktree desde `origin/develop`, sin upstream:
   `git -C <repo> worktree add --no-track -b <rama> "<AcmeOrg>/.worktrees/<repo>--<slug>" origin/develop`
   *`--no-track` a propósito:* sin él la rama queda siguiendo a `origin/develop` y un `git push` pelado apunta a develop. El primer push será `git push -u origin <rama>`.
5. Copia la configuración local que git ignora, desde la carpeta principal del repo, respetando la ruta relativa. Solo esta lista cerrada, y solo si el archivo está ignorado (`git -C <repo> check-ignore -q <archivo>`):
   - `.env` y `.env.*` (excepto `.env.example`)
   - `**/appsettings.Development.json`
   - `**/*.csproj.user`

   Fuera de `bin/`, `obj/` y `node_modules/`. Nada más: ni docs locales (`web-app/docs/CREDENCIALES-DEV.md`), ni `.claude/settings.local.json`. Los `dotnet user-secrets` no se copian porque ya se comparten (van por `UserSecretsId`, no por carpeta).
6. Dependencias: `web-app` → `npm ci` en el worktree. Los .NET no necesitan paso previo; `dotnet build` restaura.
7. Si vino `--run NNNN`, anótalo en la fila de la tarjeta del plan de ola (ver abajo).
8. Si vino `--bd-docker`, sigue la sección **BD propia en Docker** de abajo antes de reportar.
9. Reporta: ruta, rama, commit base (`git -C <ruta> rev-parse --short HEAD`), nombres de los archivos copiados, la BD si la hay (contenedor y puerto, nunca la contraseña), y el comando para trabajarlo: `/orquestar --en .worktrees/<repo>--<slug> <tarea>`.

## BD propia en Docker (`--bd-docker`)

*(2026-09-11, aprobado por el responsable del repo.)* **Solo para ramas de `api-core` que traen migración.** Todos los worktrees comparten los mismos `user-secrets`, así que sin esto todos apuntan a la misma base: dos ramas con migraciones distintas se rompen entre sí, y ninguna debe tocar la base local del responsable del repo ni la de dev.

**Qué cubre y qué no:** api-core tiene un solo `DbContext` (`CoreDbContext`), que resuelve su cadena en `PersistenceServiceRegistration.ObtenerCadenaConexionSql` — primero `ConnectionStrings:ConexionSql`, después `ConnectionStrings:CoreDb`. Eso es lo único que va a Docker. People, Contracts y Delivery api-core los consume por HTTP contra dev, en solo lectura, igual que siempre.

**Git Bash reescribe las rutas Linux** que ve en un argumento: `/opt/mssql-tools18/bin/sqlcmd` le llega a Docker como `C:/Program Files/Git/opt/...` y falla con "No such file or directory" (verificado 2026-09-11). **Todo** `docker exec` o `docker cp` con una ruta del contenedor lleva `MSYS_NO_PATHCONV=1` delante.

1. **Solo `api-core`**: con otro repo, rechaza la opción y explica por qué.
2. `docker info` debe responder; si Docker no está levantado, **para** y pídele al responsable del repo que lo inicie.
3. **Puerto**: el primero libre desde `14331` — libre significa sin `LISTENING` en `netstat -ano` y sin aparecer en `docker ps --format "{{.Ports}}"`.
4. **Contraseña**: generada al azar (`python -c "import secrets; print('Wt9!' + secrets.token_urlsafe(18))"`, el prefijo cubre la complejidad que exige SQL Server) y escrita **solo** en `AcmeOrg/.worktrees/<repo>--<slug>.bd.env`, fuera del worktree y dentro de una carpeta ignorada:
   ```
   ACCEPT_EULA=Y
   MSSQL_SA_PASSWORD=<generada>
   BD_PUERTO=<puerto>
   BD_CONTENEDOR=core-bd--<slug>
   ```
   Nunca la muestres en el chat ni la pases literal en un comando: léela del archivo dentro del mismo comando (`PW=$(sed -n 's/^MSSQL_SA_PASSWORD=//p' <archivo>)`).
5. **Contenedor** — misma imagen que los tests de integración (`DatabaseFixture.cs`):
   `docker run -d --name core-bd--<slug> --label acmeorg.worktree=<repo>--<slug> --env-file <archivo .bd.env> -p <puerto>:1433 mcr.microsoft.com/mssql/server:2022-latest`
   Espera a que acepte conexiones: reintenta `docker exec -e SQLCMDPASSWORD="$PW" core-bd--<slug> /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -C -Q "SELECT 1"` hasta 90 s. Si no levanta, muestra `docker logs --tail 30 core-bd--<slug>` y **para**.
6. **Cadena de conexión** — se arma en el comando, nunca se guarda en `user-secrets` ni en un `appsettings`:
   `CS="Server=localhost,<puerto>;Database=CoreDb;User Id=sa;Password=$PW;TrustServerCertificate=True"`
   La base se llama `CoreDb` porque `AcmeOrg/scripts/seed-crm-data-sintetica.sql` hace `USE [CoreDb]`.
   **Los scripts de semilla viven en `AcmeOrg/scripts/`, no dentro de `api-core/`** *(corregido 2026-09-14, primera ejecución real de `--bd-docker`: este archivo los daba por relativos al repo y no existen ahí).*
7. **Migraciones de la rama** — HARD RULE: antes de ejecutar, comprueba en el mismo comando que `$CS` empieza con `Server=localhost,<puerto>;` y aborta si no. Un `database update` que cae en la cadena de los `user-secrets` es exactamente lo que esto existe para evitar.
   `ConnectionStrings__ConexionSql="$CS" dotnet ef database update --project <ruta>/Persistence --startup-project <ruta>/Host --connection "$CS"`
   La variable **y** `--connection`, las dos: si una fallara, la otra sigue apuntando a Docker. El comando pide aprobación del responsable del repo por permisos; es lo esperado.
8. **Datos base**:
   - Siempre `AcmeOrg/scripts/seed-outbox-retry-policy.sql`: sin esas dos policies el job del Outbox no tiene con qué resolver reintentos (los tests de integración siembran las mismas).
     **Ese script aborta contra una base local**: trae un guard `IF DB_NAME() <> N'CRM'` puesto para Azure, donde protege de sembrar la base equivocada en un servidor compartido — pero acá la base se llama `CoreDb` y el guard corta con `ABORTADO: este script debe correr sobre la base [CRM]`. **No edites el original**: copialo al scratchpad ampliando el guard a `IF DB_NAME() NOT IN (N'CRM', N'CoreDb')` y corré la copia. Los dos `INSERT` que siembra son idempotentes (`IF NOT EXISTS`), sin `DROP` ni `DELETE`. *(Verificado 2026-09-14.)*
   - Con `--seed`, además `AcmeOrg/scripts/seed-crm-data-sintetica.sql` (casos y tareas sintéticos para probar la UI).
   - Los dos son idempotentes (`IF NOT EXISTS`, sin `DROP` ni `DELETE`). Se corren con `docker cp` + `sqlcmd -I -f 65001 -d CoreDb -i`. **`-I` es obligatorio** *(corregido 2026-09-14, primera ejecución real)*: `sqlcmd` arranca con `QUOTED_IDENTIFIER` apagado, y cualquier `INSERT` sobre una tabla con índice filtrado falla con `Msg 1934`. `-f 65001` hace que lea el script en UTF-8, sin romper las tildes. Si el script usa transacción con `XACT_ABORT`, el fallo no deja filas a medias.
   - **No** `AcmeOrg/scripts/crear-request-response-log.sql`: es el equivalente manual de una migración que el paso 7 ya aplicó.

**Levantar el Host de un worktree con BD propia:**
`ConnectionStrings__ConexionSql="$CS" dotnet run --project <ruta>/Host --launch-profile http`, en background y con la misma cadena armada desde `.bd.env`. Las variables de entorno le ganan a los `user-secrets` en el orden de configuración de ASP.NET Core, y la variable vive solo en ese proceso. **Verifica que de verdad usa Docker** antes de probar nada: con el Host arriba, espera hasta 40 s (el job del Outbox consulta la base cada 30 s) y corre contra el contenedor `SELECT COUNT(*) FROM sys.dm_exec_sessions WHERE is_user_process = 1 AND program_name NOT LIKE 'SQLCMD%'`. Debe dar más de 0: son las conexiones del Host. Si da 0, el Host está usando otra base: **bájalo y para**.

**Después de `sincronizar`**: si el merge trajo migraciones nuevas de develop, repite el paso 7 contra la misma BD antes de volver a levantar el Host.

## listar

`git -C <repo> fetch origin develop` por cada repo con worktrees en `.worktrees/`, y una tabla con una fila por worktree:

| Worktree | Rama | Adelante / atrás de develop | Sin commitear | Sin pushear | PR | BD |
|---|---|---|---|---|---|---|

- Adelante/atrás: `git -C <ruta> rev-list --left-right --count origin/develop...HEAD` (izquierda = atrás, derecha = adelante).
- Sin commitear: `git -C <ruta> status --porcelain | wc -l`.
- Sin pushear: `git -C <ruta> log --oneline origin/<rama>..HEAD` si la rama remota existe; si no, "nunca pusheada".
- PR: `gh pr list --repo <owner/repo> --head <rama> --state all --json number,state,baseRefName,url` (`<owner/repo>` sale de `git -C <repo> remote get-url origin`). Si el PR tiene `baseRefName` distinto de `develop`, márcalo en rojo: es el error que ya pasó.
- BD: si existe `.worktrees/<repo>--<slug>.bd.env`, `docker ps -a --filter label=acmeorg.worktree=<repo>--<slug> --format "{{.Status}} {{.Ports}}"`; si no, "—".

Cierra con una línea por worktree que está **atrás** de develop y ya tiene PR abierto: "conviene `sincronizar` antes de la revisión".

## sincronizar <repo>--<slug>

El paso antes de abrir el PR, y otra vez cada vez que develop avance mientras el PR espera revisión. Protege contra la regresión que el diff no muestra: dos ramas que por separado compilan y juntas no.

**Dos modos** *(pedido explícito del responsable del repo, 2026-09-11)*:
- **Paso a paso (por defecto):** al terminar cada punto (migraciones, merge, build y tests, fila de `INDEX.md`, revisión del diff), reporta el resultado en 2-3 líneas y **espera a que el responsable del repo diga "sigue"** antes de empezar el siguiente. Nunca encadenes dos puntos en el mismo turno. Los puntos 1 y 2 (árbol limpio, fetch) son solo lectura y van juntos con el de migraciones.
- **`--seguido`:** corre todos los puntos de corrido y cierra con un solo resumen.

**En los dos modos se para igual ante un problema**: snapshot compartido, conflicto no trivial, build o test que falla, configuración local en el diff. Ahí no ofrezcas seguir: muestra el problema y las opciones, y espera la decisión. `--seguido` solo se salta las confirmaciones cuando todo sale bien.

1. `git -C <ruta> status --porcelain` debe estar vacío. Si no, **para** y muestra qué hay.
2. `git -C <ruta> fetch origin develop`. Guarda la base común **antes** de mergear: `MB=$(git -C <ruta> merge-base HEAD origin/develop)`.
3. **Migraciones EF, antes del merge**: lista los `*ModelSnapshot.cs` que cambió cada lado — `git -C <ruta> diff --name-only $MB HEAD -- '*ModelSnapshot.cs'` y `git -C <ruta> diff --name-only $MB origin/develop -- '*ModelSnapshot.cs'`. Si el **mismo** snapshot aparece en los dos (hoy en api-core solo existe `Persistence/Migrations/CoreDbContextModelSnapshot.cs`), **para**: aunque git lo mezcle sin conflicto, el `.Designer.cs` de la migración de la rama describe un modelo que ya no es el de develop, y la migración hay que regenerarla después del merge. Propón los comandos exactos (`dotnet ef migrations remove` + `add`) y espera aprobación — regenerar reescribe archivos.
4. `git -C <ruta> merge origin/develop`. **Merge, nunca rebase**: la rama puede estar pusheada y en revisión (`verificar-ramas.md`: no reescribir historia). Conflictos:
   - Triviales (los dos lados agregan filas distintas, como en `INDEX.md`): resuélvelos conservando ambos lados.
   - Cualquier otro: **para**, muestra el conflicto y pregunta. No elijas un lado por tu cuenta.
5. Verificación sobre el código combinado:
   - .NET: `dotnet build` + `dotnet test` de los proyectos de unit y arquitectura. Los de integración solo si la rama toca acceso a datos (mismo criterio que el Step 4.4a de `/orquestar`).
   - `web-app`: `npm run build`, `npm run test`, `npm run lint`.
   - Si algo falla, **no lo arregles acá**: repórtalo. El arreglo va por `/orquestar --en` en la misma rama.
6. Registro de la corrida: los run docs ya no viajan en la rama — `/orquestar` los escribe directo en `docs/runs/` de la raíz de AcmeOrg *(desde 2026-09-16)*. Solo verifica que cada corrida de la rama figure en `docs/runs/INDEX.md` (mapa de conocimiento + libro mayor, formato del Step 5 de `/orquestar`); si falta, agrégala y comitea en `agentic-harness`, no en la rama. Como todas las sesiones escriben el mismo `INDEX.md`, edita filas puntuales: nunca reescribas el archivo entero.
7. Revisión previa al push (memoria `feedback-multi-repo-push-review-discipline`, regla 1): `git -C <ruta> diff --stat origin/develop...HEAD` y lectura **archivo por archivo** del diff completo buscando configuración local filtrada — cadenas de conexión, `localhost`, `.env`, restos de depuración. Señala lo sospechoso; no lo incluyas ni lo saques en silencio.
8. Reporta: merge limpio o con qué conflictos, resultado de build y tests, y si está lista para PR. **No pushea, no abre PR y no lo ofrece.** Cuando el responsable del repo lo pida: `git -C <ruta> push -u origin <rama>` y `gh pr create --base develop --body-file <archivo UTF-8>`.

## cerrar <repo>--<slug>

Solo cuando el PR ya se mergeó.

1. Verifica, y muestra el resultado de cada punto:
   - PR mergeado a `develop`: `gh pr list --repo <owner/repo> --head <rama> --state merged --json number,baseRefName,mergedAt`.
   - Worktree limpio: `git -C <ruta> status --porcelain` vacío.
   - Nada sin pushear: `git -C <ruta> log --oneline origin/<rama>..HEAD` vacío.
2. Si algo falla, **para** y dilo. Nunca `--force`.
3. Propón `git -C <repo> worktree remove "<ruta>"` y espera aprobación expresa. Borra la carpeta, incluidas las copias de configuración local.
   Si el worktree tiene BD propia, en la **misma** propuesta: `docker rm -f core-bd--<slug>` y borrar `.worktrees/<repo>--<slug>.bd.env`. Avisa que se pierden los datos de esa base (sintéticos, pero se pierden). Antes, confirma con `docker ps -a --filter label=acmeorg.worktree=<repo>--<slug>` que el contenedor es el de esta rama y no otro.
4. **La rama local y la remota no se tocan**: borrarlas es una decisión aparte que el responsable del repo pide explícitamente.

## Plan de ola

Antes de crear los worktrees de una ola se fijan las decisiones que después son caras de cambiar. Una fila por tarjeta, en la fila de la ola en `TASKS.md` o en el doc que el responsable del repo indique:

| Tarjeta | Repo | Rama | Run reservado | Áreas / archivos que toca | Migración (DbContext) | BD para probar en vivo | Interfaz que expone a otra tarjeta |
|---|---|---|---|---|---|---|---|

Reglas para armarla:
- **Dos tarjetas que tocan los mismos archivos no van en la misma ola** — o se juntan en una sola rama si son la misma pantalla/feature del mismo repo (criterio del plan del 2026-09-10).
- **Máximo una tarjeta con migración por `DbContext` por ola.** En api-core eso significa una sola por ola: `CoreDbContext` es su único `DbContext` en `develop` (verificado 2026-09-11).
- **BD para probar en vivo**: "ninguna" (frontend, o se prueba solo con tests) o "Docker propio" (`--bd-docker`), obligatoria para toda tarjeta de api-core con migración que se vaya a levantar.
- **Nunca una rama creada desde otra rama sin mergear.** Si B necesita código de A, B va en la ola siguiente.
- **Run reservado**: el siguiente número libre en `docs/runs/` de la raíz de AcmeOrg, más uno por tarjeta de la ola. Se reserva acá para que dos sesiones paralelas no tomen el mismo.
- **ADR reservado** *(desde 2026-09-16)*: si una tarjeta de la ola puede generar un ADR, el siguiente número libre en `docs/adr/` de la raíz de AcmeOrg, más uno por tarjeta que lo necesite. Mismo motivo que el run: todas las sesiones escriben en la misma carpeta.
- Si una tarjeta expone un DTO o endpoint que otra de la **misma** ola consume, la interfaz (nombres y tipos de campos) se escribe en esta tabla antes de empezar, y ninguna de las dos lo cambia sin avisar.

**Probar en vivo desde un worktree**: los puertos son los mismos que en la carpeta principal (<PORT_CORE>, 5173…). Se levanta un solo Host a la vez; antes de `dotnet build` en otro worktree no hace falta frenar nada (cada carpeta tiene su propio `bin/`), pero sí antes de levantar un segundo Host en el mismo puerto.

**Varias sesiones a la vez: un solo Host con canales activos** *(2026-09-11, pedido del responsable del repo: "si tenemos 2 sesiones o más usando WAHA, por si en algún momento se cruza")*. Los canales son recursos compartidos que ningún worktree aísla: el WAHA local (una sola sesión de WhatsApp, un solo webhook) y el buzón de correo de los `user-secrets` — el poller de api-core marca como leído (`Seen`) cada correo que registra, así que dos Hosts se roban los mensajes entre sí.
- **Antes de levantar un Host**, cualquier sesión mira si ya hay otro: `netstat -ano | grep ":<PORT_CORE> " | grep LISTENING` y el `CommandLine` de ese PID (`powershell -NoProfile -Command "(Get-CimInstance Win32_Process -Filter 'ProcessId=<pid>').CommandLine"`), para saber de qué carpeta es.
- **Si hay otro, no lo bajes**: puede ser de otra sesión o del responsable del repo. Díselo y pregunta cuál queda arriba.
- Las pruebas de WhatsApp y correo se hacen **de a una sesión por vez**. Las que no tocan canales no necesitan Host: los tests unitarios ya simulan WAHA y correo.

**WAHA: uno solo, compartido, y nunca desde un worktree** *(2026-09-11)*:
- **Nunca `docker compose -f docker-compose.waha.yml up` dentro de un worktree.** Compose toma el nombre del proyecto de la carpeta: desde `api-core/` crea `api-core-waha-1`, pero desde `.worktrees/api-core--<slug>/` crearía otro contenedor con **otro volumen de sesiones, vacío** (WhatsApp sin vincular, hay que escanear el QR de nuevo) y chocaría en el puerto 3000. El WAHA local se levanta solo desde la carpeta principal `api-core/`.
- Sirve al único Host que esté levantado: el webhook de su sesión apunta al puerto <PORT_CORE>, que es el mismo en todos los worktrees.
- Los tests no lo necesitan: unitarios con `Mock<IApiWahaService>`.
- **Nunca apuntar un worktree al WAHA de la VM de Azure** (`<host-waha>`): es el de dev.
- El número vinculado es real: una prueba de envío va solo a números propios.

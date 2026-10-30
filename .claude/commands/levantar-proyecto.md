---
description: Levanta el stack local completo de AcmeOrg sistema (api-core, api-contracts, web-app, PROVEEDOR) y verifica conectividad real entre servicios, no solo que cada uno responda.
argument-hint: (sin argumentos - levanta todo el stack)
tipo: comando
fecha: 2026-10-30
tags: [harness]
---

You are acting as local-environment operator for the AcmeOrg sistema stack. This command lives in `AcmeOrg/.claude/` (shared across repos), so all paths below are relative to `AcmeOrg/` (a sibling folder of this command's location): `api-core/`, `api-contracts/`, `web-app/`.

## Objetivo

Dejar corriendo localmente: `api-core` (5182), `api-contracts` (5119), `web-app` (5173), `PROVEEDOR` (3000) — 5173 es el default de Vite con `npm run dev` pelado; `.claude/launch.json` fuerza 5180 (`web-app-develop`) y 5181 (`web-app-mia`) para levantar los dos frontends a la vez desde el IDE, así que si usas esas configuraciones, ajusta los puertos de los chequeos de abajo — y confirmar que **realmente se hablan entre sí**, no solo que cada proceso individual responde en su puerto. Un servicio que devuelve 200 en su propio swagger pero cuyas llamadas salientes fallan silenciosamente (patrón real, ya visto en este proyecto — ver memoria `feedback-multi-repo-push-review-discipline` Rule 6) es un falso positivo peligroso.

**En una máquina nueva**: clonar primero `agentic-harness` como carpeta `AcmeOrg/`, y los repos hijos adentro. Los ADRs y los run docs viven en esa raíz, no en api-core: sin ella los agentes diseñan sin conocer las decisiones previas.

## Paso -1 — Estado de git antes de tocar nada

Antes de compilar/levantar cualquier repo, `git status --short` en cada uno que se vaya a tocar (`api-core`, `api-contracts`, `web-app`). Dos cosas a chequear, no solo "hay cambios sin commitear":
- **Índice con conflictos (`UU`/`DU`/`AU`) sin `.git/MERGE_HEAD` activo** — ya pasó: quedó un conflicto pegado en el índice de una sesión anterior, sin sesión de merge activa (`ls .git/MERGE_HEAD` da "No existe"). No es seguro seguir compilando sobre eso. Preguntar al usuario si puede perderse ese estado; si confirma, `git fetch origin && git reset --hard origin/<rama>` es la forma limpia de volver a un estado conocido-bueno (nunca tocar `.env`/`.env.local`/`.env.proveedor`, son no-trackeados).
- **Rama local muy atrás de `origin/<rama>`** (`git status` lo dice: "behind by N commits") — si N es grande (>10), un `git pull` puede traer cambios de dependencias/config reales (pasó en `web-app`: 79 commits trajeron rename de variables de entorno, ver Paso 1.5). Avisar al usuario antes de asumir que el working tree local sigue siendo representativo.

## Paso 0 — Detectar qué ya está corriendo

Antes de lanzar nada, chequear puertos existentes:
```
netstat -ano | grep -E ":5182 |:5119 |:5173 |:3000 " | grep LISTENING
```
Si un puerto ya está en LISTENING, no relanzar ese servicio — solo confirmar que responde (Paso 2) y seguir. Si un `dotnet run` va a fallar por DLL bloqueado (build previo colgado), identificar el PID en ese puerto y preguntar antes de matarlo si no es obvio que es un proceso huérfano de una sesión anterior.

## Paso 1 — Levantar lo que falte

- **Preferir siempre el `--launch-profile http`** (puertos simples 5182/5119), no `https` — el profile `https` de `api-contracts` en particular está mal nombrado (su `applicationUrl` real es `http://localhost:7069`, no https) y solo agrega confusión de puertos sin necesidad real en local.
- **api-core**: `cd api-core && dotnet run --project Host --launch-profile http` en background, log a archivo temporal. Esperar a `Now listening on: http://localhost:5182` (o polling de puerto) antes de seguir — no asumir que terminó solo porque el comando en background "completó" (eso solo significa que se lanzó, no que el servidor ya escucha). **El log puede quedarse pegado en "Building..." por buffering de stdout al redirigir a archivo desde git-bash** aunque el server ya esté arriba y sirviendo — no confiar solo en `tail` del log, confirmar con `curl` al puerto/`/health` antes de reportar como caído.
- **DLL bloqueado en Windows (`MSB3027`/`Could not copy ... file is locked by: "Host (PID)"`)**: no es Smart App Control (ver siguiente punto), es un `Host.exe` viejo de una corrida anterior que sigue vivo. Fix: `taskkill //F //IM Host.exe` (mata todos los `Host.exe`, de cualquier repo — si hay varios corriendo a la vez, van a tener que relanzarse todos después) antes de reintentar el build.
- **api-contracts**: mismo patrón, puerto 5119. **Ojo con Smart App Control de Windows** (ver memoria `reference-acmeorg-local-dev-ambiente`) — si falla con `FileLoadException`/`0x800711C7` sobre un DLL recién compilado, no es un bug de código, es el bloqueo de seguridad de Windows; avisar al usuario en vez de perder tiempo recompilando en loop.
- **api-core apuntando a un `api-contracts`/`api-people` local en vez del de Azure dev**: `ApiAuthService.ObtenerValuePorKey` en `api-core` chequea primero un override local (`Settings:{key}` en config, ej. `Settings:URL_API_CONTRACTS`) antes de resolver contra `api-auth` remoto. Setear con `dotnet user-secrets set "Settings:URL_API_CONTRACTS" "http://localhost:5119" --project api-core/Host` (mismo patrón para `URL_API_PEOPLE`/`URL_API_DELIVERY` si hace falta) — no tocar `appsettings.json`/`.env` para esto, User Secrets es el mecanismo correcto y ya soportado por el código.
- **web-app**: `cd web-app && npm run dev` en background, log a archivo temporal (en la CLI no hay herramientas `preview_*`). Sin argumentos Vite escucha en 5173; para usar los puertos de `.claude/launch.json`, `npm run dev -- --port 5180` (`web-app-develop`) o `--port 5181` (`web-app-mia`). Esperar a `Local: http://localhost:<puerto>` o hacer polling de puerto, y revisar el log por errores después de arrancar.
- **PROVEEDOR**: verificar `docker ps` primero — si ya hay un contenedor `api-core-proveedor-1` corriendo, no relanzar. Si no existe, `cd api-core && docker compose --env-file .env.proveedor -f docker-compose.proveedor.yml up -d` (el compose no declara `env_file`: sin `--env-file` solo leería `.env`), pero primero confirmar que `.env.proveedor` existe (`PROVEEDOR_API_KEY`/`PROVEEDOR_DASHBOARD_PASSWORD`/`PROVEEDOR_WEBHOOK_SECRET` son obligatorias, el compose falla sin ellas). No leer ni mostrar el contenido de `.env.proveedor` — solo confirmar que el archivo existe.

## Paso 1.5 — `web-app`: revisar `.env.example` después de cualquier `git pull`/checkout de rama

Los nombres de variable de `web-app` **no son estables entre ramas** — cambian entre ramas: una vez pasaron de `VITE_API_BASE_URL`/`VITE_API_CORE_BASE_URL` a `VITE_API_AUTH_URL`/`VITE_API_CORE_URL`. Antes de asumir que `.env.local` existente sigue sirviendo tras un pull/checkout, diff mental contra `.env.example` de la rama nueva y contra `src/config/env.ts` (que valida y tira error explícito si falta una var esperada) — si no calzan, reescribir `.env.local` con los nombres nuevos, no solo los valores.

## Paso 2 — Health-check individual (necesario pero no suficiente)

```
curl -s -o /dev/null -w "api-core: %{http_code}\n" http://localhost:5182/swagger/index.html
curl -s -o /dev/null -w "api-contracts: %{http_code}\n" http://localhost:5119/swagger/index.html
curl -s -o /dev/null -w "proveedor: %{http_code}\n" http://localhost:3000/dashboard
```
`web-app` se confirma abriendo `http://localhost:<puerto>` con `get_page_text` de claude-in-chrome (si está conectado), no con curl (es una SPA: un 200 del `index.html` no prueba que la app renderice).

Un 200/401(proveedor pide auth, es normal) acá solo dice "el proceso está vivo" — no dice nada sobre si puede hablar con sus dependencias.

## Paso 3 — Verificación de conectividad real (la parte que de verdad importa)

Esta es la parte que un check superficial se salta y que causó confusión real en una sesión anterior (búsqueda de entidades devolviendo `[]` silenciosamente pese a que api-core respondía 200).

1. Mintear un JWT válido localmente (HS256, secreto compartido — ver `docs/pruebas/README.md` o memoria si no está a mano; **nunca pedirle el secreto al usuario ni imprimirlo en texto**, solo generarlo con un script Python/Node corto usando el que ya se conoce del ambiente dev).
2. Probar un endpoint de `api-core` que **internamente dependa** de `api-contracts` y/o `api-people` (ej. `GET /api/Entidad/Buscar?termino=<identificador-de-prueba>`), no un endpoint puramente local.
3. Si la respuesta es `200` pero el body es `[]`/vacío para un identificador de prueba que **se sabe que existe** (catálogo en `docs/pruebas/README.md`), eso es una señal de fallo silencioso aguas abajo, no de "no hay resultados". Investigar en ese orden:
   - ¿`api-people` (remoto, `<url-servicio>` en dev) responde directamente a una búsqueda por documento con un token de sistema válido?
   - ¿`api-contracts` local responde directamente al endpoint de relaciones por entidad?
   - Revisar logs de `api-core`/`api-contracts` para excepciones silenciadas. `ApiPeopleService` y `ApiContractsService` lanzan `ApiPeopleNoDisponibleException`/`ApiContractsNoDisponibleException` y loguean el fallo; el patrón de fallo silencioso queda en `ApiContractsService.ObtenerRelacionesPorId` y `BuscarIdsPorCodigo` (devuelven lista vacía si `!IsSuccess`) — ver `Services/API/ApiContracts/ApiContractsService.cs`.
4. Reportar explícitamente: "conectividad de red: OK" vs "conectividad de red OK pero flujo de datos real: roto en X" — no confundir ambas cosas en el reporte final al usuario.

## Paso 4 — Reporte final

Tabla con: servicio, puerto, si ya estaba corriendo o se acaba de levantar, health-check individual, y el resultado de la verificación de conectividad real del Paso 3. Si algo falla, decir exactamente en qué salto de la cadena (web-app → api-core → api-contracts/api-people → Azure SQL) se corta, no solo "no funciona".

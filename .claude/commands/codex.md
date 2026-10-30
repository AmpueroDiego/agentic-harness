---
description: Revisión de código con Codex CLI (OpenAI) antes del push, como segundo revisor junto al QA en el pipeline completo o en tareas avanzadas, y coder de lo mecánico. Solo si la cuenta de Codex tiene cuota disponible; si no, se omite sin bloquear.
argument-hint: <ruta del repo o worktree> [--base develop | --commit <sha> | --uncommitted] [foco de la revisión]
---

# /codex

Segundo revisor local: corre `codex exec review` sobre un diff y trae sus hallazgos para verificarlos contra el código, igual que se hace con los comentarios de Codex en los PRs, pero **antes del push**. Nació el 2026-09-14: en los PRs api-core #24 y web-app #12 Codex encontró 18 cosas en tres rondas después de subir el código; revisar antes corta esas rondas.

Pedido: $ARGUMENTS

## Cuándo usarla

- **Como revisor, siempre antes de abrir un PR** *(el responsable, 2026-10-01)*: es la puerta previa a [`/supercodex`](supercodex.md). Se corre sobre `--base develop` con la rama ya con QA, se verifican los hallazgos contra el código, los P2 o más graves se corrigen y se repite hasta **dos pasadas limpias seguidas con `--base develop` (tope 4)**, **y recién entonces** se sube la rama y se abre el PR (con [`entregar-pr.sh`](../scripts/entregar-pr.sh)). Eran una pasada (tope 3) hasta el 2026-10-07: web-app #73 acumuló ~17 hallazgos con el PR ya abierto. Origen: en las PRs de la ola del 01/10 (api-core #65 y #66, web-app #61, #62 y #63) Codex dejó de 1 a 5 hallazgos P2 por PR *después* de abrirlos, cada uno con su commit, su respuesta y otra ronda; la misma revisión en local los habría atrapado antes. **Arreglos sobre un PR ya abierto** *(2026-10-09)*: una pasada limpia sobre el delta del lote, antes del push (ver `/supercodex`, "Local primero, el bot una vez por lote"). Como coder de lo mecánico sigue primero en la fila mientras tenga créditos.
- **Como coder**, dentro del reparto de un coder por motor de `/orquestar` (Step 3): a Codex le toca lo mecánico con un archivo con dueño.
- **Solo con cuota de Codex disponible.** La cuota es de la cuenta de ChatGPT del responsable. Si se agotó, se omite y se dice en una línea; nunca bloquea la corrida.
- Complementa al QA y a `adversary`, no los reemplaza.

## Requisitos

- `codex --version` responde (instalado con `npm i -g @openai/codex`).
- `codex login status` dice `Logged in`. Si no, **no** pedir credenciales en el chat: pedirle al responsable que escriba `! codex login`.
- **Todo `codex exec` del pipeline lleva `-c model_provider=openai`** *(2026-09-23)*: `~/.codex/config.toml` tiene un bloque `CCR managed profile` de claude-code-router que desvía Codex a un gateway local con modelos gratis de OpenRouter, y ahí falla con `401 ... Invalid or expired API key`. El bloque es del responsable y se deja; la bandera fuerza la cuenta de ChatGPT solo en esa llamada. El ping de créditos se hace con la misma bandera y con el modelo más barato: `codex exec --ephemeral -s read-only -c model_provider=openai -m gpt-6-luna -c model_reasoning_effort="low" "Responde solo: OK" < /dev/null` (~4K tokens; con el modelo por defecto, astra, costaba ~16-21K).
- **Codex sí compila .NET** *(2026-09-24)*: el sandbox le bloqueaba `NuGet.Config`. Arreglo: el orquestador corre `dotnet restore` en la raíz antes de lanzarlo, y Codex va con `--add-dir "$APPDATA/NuGet" --add-dir "$USERPROFILE/.nuget" --add-dir "$USERPROFILE/.dotnet"` y compila con `dotnet build <sln> --no-restore`. Probado en la ola 3: build verde. `dotnet ef migrations add` sigue sin correr adentro (falla el logger del entorno): la migración la genera el orquestador; si Codex la escribe a mano, le falta el `.Designer.cs` y EF no la encuentra.

## Cómo correrla

1. Elegir el alcance según lo que haya:
   - rama sin PR o antes del push: `--base develop` (o `origin/develop` si la local está atrasada);
   - un commit ya hecho: `--commit <sha>`;
   - cambios sin commitear (lo normal después del coder): `--uncommitted`.
2. Correr desde la carpeta del repo o worktree, en solo lectura y sin guardar la sesión. **El alcance (`--commit`, `--base`, `--uncommitted`) no admite instrucciones propias** (el CLI rechaza `--commit` junto a un prompt, verificado con 0.154.0): se usa la revisión nativa de Codex, la misma que hace en los PRs, y la traducción y el formato los hace el orquestador al leerla.
   ```bash
   cd <repo-o-worktree> && codex exec review <alcance> --ephemeral -c model_provider=openai -c service_tier="fast" -m gpt-6.1-sol -c sandbox_mode="read-only" -o "<scratchpad>/codex-review.md"
   ```
   Si hace falta un foco concreto (por ejemplo, solo la migración), usar en su lugar `codex exec -C <repo-o-worktree> -s read-only --ephemeral -c model_provider=openai -c service_tier="fast" -m gpt-6-luna -o "<scratchpad>/codex-review.md" "Revisa el diff de git diff origin/develop...HEAD enfocándote en <foco>. Solo hallazgos reales con prioridad, archivo:línea y escenario de falla."`.
   Correrlo en segundo plano (`run_in_background`) y seguir con lo demás: tarda varios minutos.
   **`-m` va explícito también en modo `review`** (ver sección "Modelo" más abajo). **Si falla con `setup refresh had errors`** (sandbox de Windows, visto el 2026-10-19): agregar `-c windows.sandbox=\"unelevated\"`, o pasarle el diff dentro del prompt con `codex exec - -s read-only ... < prompt.md`, que no necesita ejecutar nada. **En diffs de UI, sumar al prompt el chequeo de foco** *(el responsable, 2026-10-19: 5 hallazgos P2 iguales en un día)*: «si un control con foco se desmonta o se deshabilita (al terminar una carga, resolver un conflicto o cerrar un aviso), ¿adónde va el foco? Si cae en `body` o fuera del modal, es hallazgo». **`--add-dir` no existe en modo `review`** (`error: unexpected argument`) — es exclusivo del modo coder de la sección de abajo; en modo review no hace falta, es de solo lectura.
   **Ramas apiladas (una PR trae mergeada a la anterior): una sola pasada en la más completa.** Si `#37` ya trae `#35` adentro y `#39` ya trae `#35`+`#37`, revisar solo `#39` contra `develop` cubre las tres sin pagar el código repetido tres veces.
3. **Si la salida menciona límite de uso** (`usage limit`, `rate limit`, `quota`, `limits have been reached`): no reintentar; reportar "Codex sin cuota, revisión omitida" y seguir.
4. Leer `codex-review.md`.

## Qué hacer con los hallazgos

- **Verificar cada uno contra el código antes de creerlo.** Codex acierta mucho, pero no siempre: marcar cada hallazgo como real o falso positivo, con el motivo.
- Los reales van al coder **en el mismo paquete que los del QA** (Step 4 de `/orquestar`), no en un viaje aparte.
- Los que son decisión de negocio (canal de una interacción, qué va a producción) se le presentan al responsable uno por uno, en el orden en que los dio Codex, con recomendación; no se arreglan por cuenta propia.
- En el run doc y en el reporte final: cuántos hallazgos, cuántos reales, cuántos corregidos, o "omitida: sin cuota".

## Lo que no hace

- No comenta en GitHub. Los comentarios de Codex en los PRs se siguen atendiendo como hasta ahora.
- No usa `--dangerously-bypass-approvals-and-sandbox`.
- No toma decisiones: qué código muerto se elimina, cómo queda un esquema o qué va a producción lo decide el responsable, igual que con cualquier agente.

## Modelo: `gpt-6.1-sol` (coder y revisión) *(2026-09-26; 6.1-sol desde 2026-10-14; coder sol desde 2026-10-22)*

**Esfuerzo del coder** *(el responsable, 2026-10-27)*: `medium` por defecto; **`high` en código de estado y concurrencia de web-app** (un provider de estado, un hook de recarga, avisos, SignalR) con `CODEX_EFFORT=high`. Ese día #143 dio 4 vueltas por casos borde de concurrencia que el coder en medium no anticipó. Toda tarea del coder que toque estado asíncrono lleva este chequeo: *«¿qué pasa si llega tarde la respuesta de un intento anterior, o si el usuario reintenta o cambia de sesión a mitad?»*.

**Se pasa `-m` explícito siempre**; `flujo.sh` rechaza cualquier otro modelo. Con la CLI 0.157.1 ambos responden con la cuenta actual (133 usos de `gpt-6-luna` en las sesiones del 2026-09-26).

| Nombre | Qué pasa |
|---|---|
| `gpt-6-luna` | **Funciona.** Solo coder de lo mecánico (renombres, fixtures) con `CODEX_MODEL_CODER=gpt-6-luna`: el 2026-10-22 obligó a 2-3 vueltas por tarjeta y el coder por defecto pasó a sol |
| `gpt-6-sol` | **Funciona.** Solo revisión, como alternativa a 6.1-sol |
| `gpt-6.1-luna` | **No habilitado** para la cuenta de ChatGPT («not supported when using Codex with a ChatGPT account»), probado con las CLI 0.162.1 y 0.163.0 el 2026-10-19 |
| `gpt-6.1-sol` | **Funciona desde la CLI 0.162.1** (con 0.157.1 daba «not supported when using Codex with a ChatGPT account»). QA, adversary y revisión, por decisión del responsable del 2026-10-14 |
| `gpt-5.6-luna` | Ya no se usa |

En las sesiones previas de Codex (`~/.codex/sessions/`) figuran los que realmente se usaron alguna vez — `gpt-5.6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-6-astra`. **Ese es el lugar donde mirar**, porque la CLI **no tiene comando para listar modelos** (`codex models` no existe y `-m` acepta cualquier string).

**Tres fallos distintos que no se distinguen por el código de salida**, los tres vistos el mismo día:

| Síntoma | Qué significa |
|---|---|
| `Model metadata for X not found. Defaulting to fallback` | Ese nombre no existe |
| `400 ... not supported when using Codex with a ChatGPT account` | El nombre existe pero esta cuenta no lo habilita |
| `Your workspace is out of credits` | Cuota agotada **de ese modelo**, no de la cuenta entera: el 2026-09-21 astra quedó seco y `gpt-5.6-luna` siguió respondiendo |

Siempre leer la salida: ninguno de los tres se distingue por el exit code.

**Y una consecuencia operativa:** una corrida que se queda sin cuota **a mitad** deja el worktree con trabajo a medias, sin compilar y a veces tocando archivos fuera del alcance dado. Antes de seguir, `git status` y `git diff`; y se **termina**, no se rehace desde cero.

## Codex como coder

Con `--sandbox workspace-write` Codex escribe en el worktree.

```bash
cd <worktree> && codex exec --sandbox workspace-write -m gpt-6.1-sol -c model_provider=openai -c service_tier="fast" -c windows.sandbox=\"unelevated\" -c model_reasoning_effort="medium" "$(cat <tarea>.md)" < /dev/null
```

**En esta máquina no está instalado `rg` (ripgrep)** *(2026-09-22, corrida 0057)*: Codex lo intenta por defecto para buscar en el repo y falla con `CommandNotFoundException`. No lo bloquea —cae a leer archivos uno por uno— pero le cuesta tokens y tiempo. Va como nota de entorno al final de cada prompt: *"en esta máquina NO está instalado `rg`; usá `grep -rn` o `findstr`"*.

**Siempre con `< /dev/null` al lanzarlo en segundo plano** *(2026-09-16)*: si la entrada estándar queda abierta, `codex exec` escribe `Reading additional input from stdin...` y **se queda esperando para siempre** sin tocar ningún archivo. Pasó en la corrida 0047: 15 minutos colgado hasta cortarlo. El comando correcto es `codex exec ... "$(cat <tarea>.md)" < /dev/null`.

**Cuándo sí**, y las condiciones no son negociables:
- **Un archivo con dueño exclusivo.** Nunca un cambio que cruce varios archivos con dependencias entre sí — ahí el ida y vuelta con un `coder`/`coder-web` sale más barato.
- **Criterio objetivo y verificable**: "que no quede ninguna clase `dark:` en este archivo" sí; "mejorá la jerarquía visual" no.
- El prompt le nombra **explícitamente qué archivos tiene prohibido tocar** y quién es el dueño de cada uno, igual que a un coder propio. La tarea se le pasa desde un `.md` en el scratchpad (UTF-8), no como argumento con tildes.
- **Su diff se contrasta contra `git status`**, igual que el de cualquier coder. En la primera prueba declaró su alcance con honestidad ("Modifiqué únicamente `AccountTabs.tsx` y su test") y era cierto — pero eso se verifica, no se asume.

**Qué hizo la primera vez** (2026-09-15, corrida de la auditoría de UX): reescribió `getEntityTheme` en `AccountTabs.tsx` para sacarle la variante `dark:` de Tailwind —que seguía al sistema operativo en vez de al tema de la app—, dejó un test que rechaza que alguien la vuelva a meter, corrió sus tres comandos de verificación y reportó el resultado de cada uno. Respetó el alcance con otros tres coders trabajando en el mismo worktree.

**Lo que no vio:** que al limpiar los estilos se llevó también la *forma* del badge (padding, radio, borde), que quedó como texto suelto. Lo encontró Antigravity revisando lo visual. Es el argumento de por qué un coder —humano o no— no es su propio revisor.

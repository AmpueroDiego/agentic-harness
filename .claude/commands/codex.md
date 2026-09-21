---
description: Revisión de código con Codex CLI (OpenAI) antes del push, como segundo revisor junto al QA, en toda corrida salvo Nivel 0, y coder de lo mecánico. Solo si la cuenta de Codex tiene crédito disponible; si no, se omite sin bloquear.
argument-hint: <ruta del repo o worktree> [--base develop | --commit <sha> | --uncommitted] [foco de la revisión]
---

# /codex

Segundo revisor local: corre `codex exec review` sobre un diff y trae sus hallazgos para verificarlos contra el código, igual que se hace con los comentarios de Codex en los PRs, pero **antes del push**. Nació el 2026-09-14: en dos PRs grandes Codex encontró 18 cosas en tres rondas después de subir el código; revisar antes corta esas rondas.

Pedido: $ARGUMENTS

## Cuándo usarla

- **En toda corrida salvo Nivel 0** *(ampliado el 2026-09-16; antes era solo en tareas avanzadas)*: El responsable del repo pidió usar Codex "en lo posible" para no gastar todo el presupuesto de Claude. En una corrida posterior encontró 2 hallazgos reales en un flujo de reintento, uno grave.
- **Como coder**, dentro del reparto de un coder por motor de `/orquestar` (Step 3): a Codex le toca lo mecánico con un archivo con dueño.
- **Solo con crédito de Codex disponible.** El crédito es de la cuenta de ChatGPT del responsable del repo. Si se agotó, se omite y se dice en una línea; nunca bloquea la corrida.
- Complementa al QA y a `adversary`, no los reemplaza.

## Requisitos

- `codex --version` responde (instalado con `npm i -g @openai/codex`).
- `codex login status` dice `Logged in`. Si no, **no** pedir credenciales en el chat: pedirle al responsable del repo que escriba `! codex login`.

## Cómo correrla

1. Elegir el alcance según lo que haya:
   - rama sin PR o antes del push: `--base develop` (o `origin/develop` si la local está atrasada);
   - un commit ya hecho: `--commit <sha>`;
   - cambios sin commitear (lo normal después del coder): `--uncommitted`.
2. Correr desde la carpeta del repo o worktree, en solo lectura y sin guardar la sesión. **El alcance (`--commit`, `--base`, `--uncommitted`) no admite instrucciones propias** (el CLI rechaza `--commit` junto a un prompt, verificado con 0.154.0): se usa la revisión nativa de Codex, la misma que hace en los PRs, y la traducción y el formato los hace el orquestador al leerla.
   ```bash
   cd <repo-o-worktree> && codex exec review <alcance> --ephemeral -c sandbox_mode="read-only" -o "<scratchpad>/codex-review.md"
   ```
   Si hace falta un foco concreto (por ejemplo, solo la migración), usar en su lugar `codex exec -C <repo-o-worktree> -s read-only --ephemeral -o "<scratchpad>/codex-review.md" "Revisa el diff de git diff origin/develop...HEAD enfocándote en <foco>. Solo hallazgos reales con prioridad, archivo:línea y escenario de falla."`.
   Correrlo en segundo plano (`run_in_background`) y seguir con lo demás: tarda varios minutos.
3. **Si la salida menciona límite de uso** (`usage limit`, `rate limit`, `quota`, `limits have been reached`): no reintentar; reportar "Codex sin crédito, revisión omitida" y seguir.
4. Leer `codex-review.md`.

## Qué hacer con los hallazgos

- **Verificar cada uno contra el código antes de creerlo.** Codex acierta mucho, pero no siempre: marcar cada hallazgo como real o falso positivo, con el motivo.
- Los reales van al coder **en el mismo paquete que los del QA** (Step 4 de `/orquestar`), no en un viaje aparte.
- Los que son decisión de negocio (canal de una interacción, qué va a producción) se le presentan al responsable del repo uno por uno, en el orden en que los dio Codex, con recomendación; no se arreglan por cuenta propia.
- En el run doc y en el reporte final: cuántos hallazgos, cuántos reales, cuántos corregidos, o "omitida: sin crédito".

## Lo que no hace

- No comenta en GitHub. Los comentarios de Codex en los PRs se siguen atendiendo como hasta ahora.
- No usa `--dangerously-bypass-approvals-and-sandbox`.
- No toma decisiones: qué código muerto se elimina, cómo queda un esquema o qué va a producción lo decide el responsable del repo, igual que con cualquier agente.

## Codex como coder *(agregado 2026-09-15)*

Hasta el 2026-09-15 este archivo decía que Codex "no escribe código, el arreglo lo hace el coder de `/orquestar`". **Eso ya no es cierto**: con `--sandbox workspace-write` escribe en el worktree, y funcionó bien la primera vez que se probó.

```bash
cd <worktree> && codex exec --sandbox workspace-write -c model_reasoning_effort="high" "$(cat <tarea>.md)"
```

**Siempre con `< /dev/null` al lanzarlo en segundo plano** *(2026-09-16)*: si la entrada estándar queda abierta, `codex exec` escribe `Reading additional input from stdin...` y **se queda esperando para siempre** sin tocar ningún archivo. Pasó en una corrida: 15 minutos colgado hasta cortarlo. El comando correcto es `codex exec ... "$(cat <tarea>.md)" < /dev/null`.

**Cuándo sí**, y las condiciones no son negociables:
- **Un archivo con dueño exclusivo.** Nunca un cambio que cruce varios archivos con dependencias entre sí — ahí el ida y vuelta con un `coder`/`coder-web` sale más barato.
- **Criterio objetivo y verificable**: "que no quede ninguna clase `dark:` en este archivo" sí; "mejorá la jerarquía visual" no.
- El prompt le nombra **explícitamente qué archivos tiene prohibido tocar** y quién es el dueño de cada uno, igual que a un coder propio. La tarea se le pasa desde un `.md` en el scratchpad (UTF-8), no como argumento con tildes.
- **Su diff se contrasta contra `git status`**, igual que el de cualquier coder. En la primera prueba declaró su alcance con honestidad ("Modifiqué únicamente el componente y su test") y era cierto — pero eso se verifica, no se asume.

**Qué hizo la primera vez** (2026-09-15, corrida de la auditoría de UX): reescribió una función de tema de un componente de pestañas para sacarle la variante `dark:` de Tailwind —que seguía al sistema operativo en vez de al tema de la app—, dejó un test que rechaza que alguien la vuelva a meter, corrió sus tres comandos de verificación y reportó el resultado de cada uno. Respetó el alcance con otros tres coders trabajando en el mismo worktree.

**Lo que no vio:** que al limpiar los estilos se llevó también la *forma* del badge (padding, radio, borde), que quedó como texto suelto. Lo encontró Antigravity revisando lo visual. Es el argumento de por qué un coder —humano o no— no es su propio revisor.

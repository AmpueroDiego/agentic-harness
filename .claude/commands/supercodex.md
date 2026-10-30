---
tipo: comando
fecha: 2026-10-30
tags: [codex, revision]
description: Puerta de Codex antes de pasar un PR a revisión de Revisor Principal — rondas de `@codex review` en paralelo, con contador por PR; un PR está listo con 2 rondas limpias seguidas.
argument-hint: [repo#PR ...]
---

PRs pedidos: $ARGUMENTS (si viene vacío, todos los PR abiertos de `api-core` y `web-app`; el resto de los repos no se revisa con Codex).

Relacionados: [`/cola`](cola.md) (orden de mergeo), [`/orquestar`](orquestar.md) (aplica las correcciones) y [`/trello`](trello.md) (mueve la tarjeta, solo si el responsable lo pide).

**Prioridad** *(el responsable, 2026-10-01: "eso siempre es prioridad")*: los hilos de Codex y los PRs abiertos van **antes** que cualquier tarjeta nueva. No se arranca trabajo nuevo mientras haya un hilo sin responder o un PR sin sus 2 rondas limpias; se comprueba con [`/listo-para-merge`](listo-para-merge.md).

**Precondición** *(el responsable, 2026-10-01)*: la rama llega a esta puerta con dos `/codex` locales limpios seguidos (revisión previa al push, ver [`/codex`](codex.md)). Si el PR se abrió sin esa pasada, correrla en el worktree y corregir los hallazgos antes de pedir la primera ronda: `@codex review` en el PR es la segunda mirada, no la primera. En un arreglo sobre un PR ya abierto, alcanza **una** pasada local limpia sobre el delta, pero va **antes** del push, no en paralelo *(el responsable, 2026-10-09; reemplaza la regla del 2026-10-07)*.

**Local primero, el bot una vez por lote** *(el responsable, 2026-10-09)*: el bot del PR es lento (2-4 min por ronda, más los comentarios rezagados) y cada ronda con hallazgos reinicia el contador; #<n> llegó a 15 revisiones del bot y 50 hilos. Por eso:
- Todos los hallazgos de una ronda se corrigen **juntos**, en un solo lote, y se sube **un** push. Nunca un push por hilo.
- Antes de ese push, `codex review` local sobre el delta (`/codex`, o `codex exec -s read-only` con el diff `<sha-anterior>..HEAD`) hasta que salga limpio. El 2026-10-09 la pasada local atrapó en #<n> un P2 que el propio arreglo había introducido: habría sido otra ronda del bot.
- Cada arreglo entra con el test que reproduce el hallazgo (escrito antes del arreglo): un hilo que se cierra sin test es el que el bot reabre.
- Solo después: las 2 rondas del bot sobre ese commit, una tras otra.
- PR de más de ~400 líneas o con más de 2 rondas con hallazgos: proponer partirlo en PRs apilados (git y `gh`, sin herramientas extra: ver "Pila de PRs" en [`/worktree`](worktree.md)) en vez de seguir rondando.

Esta puerta va **antes** de mover una tarjeta a `En revisión (Revisor Principal)`; mientras tanto la tarjeta puede vivir en `En revisión (el responsable)`. Nació el 2026-09-29: Codex a veces encuentra algo distinto en cada pasada, así que un solo review limpio no basta.

## Qué es una ronda limpia

Se dispara con un comentario `@codex review` en el PR; el instante en que se comentó es `T`. La ronda termina cuando el comentario-resumen de Codex (marcado `codex-pull-request-review-summary`, en `issues/<n>/comments`) muestra **Code Review** y **Security Review** como `Completed` con hora posterior a `T`.

Es **limpia** solo si, además, después de `T`:
- no hay comentarios en línea de Codex (`pulls/<n>/comments`, usuario `chatgpt-codex-connector[bot]`), ni un review suyo con observaciones (`pulls/<n>/reviews`);
- el security review dice "No security issues were found".

Cualquier otra cosa es una ronda **con hallazgos**. Si Codex no termina en ~10 minutos, se informa tal cual, no se cuenta como limpia.

**`Completed` es necesario, no suficiente** *(2026-10-07)*: Codex ya no deja comentario propio cuando la ronda sale limpia, y los comentarios en línea pueden llegar minutos después del `Completed`. La ronda se da por limpia solo tras esperar unos minutos más y releer: sin comentarios en línea ni hilos abiertos.

## Contador (uno por PR, independiente)

- Cada PR tiene su propio contador de rondas limpias seguidas, y una cuenta de rondas totales.
- **2 limpias seguidas** → el PR queda **listo** (el responsable bajó de 3 a 2 el 2026-09-29). Una ronda "sin respuesta" entre dos limpias no las separa ni reinicia el contador.
- **Una ronda con hallazgos** → el contador de limpias vuelve a **0** y se cuentan 2 más después de corregir. Ejemplo: 1 limpia, la segunda trae algo, se corrige, hacen falta 2 limpias nuevas.
- **Tope 8 (5 normal; de 6 a 8 solo con merges o refactors intermedios, dicho en el reporte)** rondas totales por PR *(retro 2026-10-27; antes 6)*. Si se llega sin 2 limpias seguidas, se para y se le pregunta al responsable, con la opción de aceptar el resto como seguimiento. Un merge de develop limpio no reinicia el conteo. Lo hace cumplir `registrar_ronda.py`: cada ronda local se anota con `python .claude/tools/supercodex/registrar_ronda.py <repo> <tarjeta> <PASS|FINDINGS> [--pr N] [--bloqueantes N] [--no-bloqueantes N] [--resumen "..."]` (no a mano en `rondas-codex.tsv`), que sale 3 con `TOPE` en la 8.ª sin 2 limpias; y `supercodex-ciclo.sh` no dispara `@codex review` (sale 5) si las filas con ese `#PR` ya llegaron al techo. Límite: las rondas anotadas sin `#PR` (antes de abrirlo) solo cuentan por tarjeta.
- **Hallazgo aceptado fuera de alcance** (el responsable, 2026-09-29): si el responsable decide que el hallazgo va a una tarjeta aparte y se responde su hilo, esa ronda cuenta como limpia. Se anota como "limpia, con un hallazgo fuera de alcance aceptado". **Desde 2026-10-07 lo decide la regla de gravedad** de [`/orquestar`](orquestar.md) (Modo Enjambre), sin preguntar: P3, deuda previa y P2 raros o cosméticos van a tarjeta de seguimiento y no reabren vuelta.
- Llevar el estado en una tabla en el scratchpad (`supercodex-estado.md`): repo, PR, commit revisado, limpias seguidas, rondas totales, estado.

## Ciclo

1. **Antes de contar rondas**, cada PR debe estar al día con `develop` (`gh pr update-branch`), y en web-app verificado en local con `bash .claude/scripts/verificar-pr.sh <PR>` porque su CI solo corre al abrir el PR (memoria `project_web_app_ci_solo_al_abrir_no_se_toca`). No se cuenta una ronda sobre una rama atrasada. Antes de las rondas finales, además, **sincronizar la cola**: mergear las ramas previas de la cola, para no repetir rondas. Y contar hilos abiertos **y** comentarios de Codex sin respuesta nuestra (el script del paso 4 se niega solo con hilos abiertos; lo otro se cuenta con el `gh api` del paso 4b).
2. **Disparar la ronda en todos los PRs a la vez**, en un mismo mensaje. Nunca uno por uno en serie: cada PR lleva su propio ritmo. **Un solo `@codex review` por vez** *(el responsable, 2026-10-20; reemplaza "las 2 rondas van juntas" del 2026-10-07)*: el script dispara uno y no se agrega otro a mano. Dos pedidos en el mismo minuto se juntan en una sola ronda del bot. La segunda ronda se pide recién cuando la primera terminó limpia; una con hallazgos deja el contador en 0.
   ```
   gh pr comment <n> -R <org>/<repo> --body '@codex review'
   ```
3. **Esperar y leer** cada PR por separado (una espera de fondo para todos, sin polling corto; una ronda tarda unos 2 a 4 minutos). Leer con `gh api` los tres endpoints de arriba, filtrando por hora posterior a `T`.
4. **Clasificar cada PR** en esa vuelta: limpia (suma 1), con hallazgos (a cero) o sin respuesta. Cada ronda se anota en [`docs/runs/supercodex-rondas.md`](../../docs/runs/supercodex-rondas.md) con su número de ejecución y la prioridad (P0–P3) de cada hallazgo; si la ronda trae hallazgos, también su bloque de detalle con la plantilla de ese archivo. Es normal que unos PRs terminen sus 2 limpias y otros sigan con errores: los que están listos salen de la lista y no se vuelven a disparar.
5. **Repetir** solo con los PRs que aún no están listos ni bloqueados.

## Cuando hay hallazgos

1. **Verificar cada hallazgo contra el código** (`grep`/`Read`) antes de decir que es real. Un hallazgo de Codex sola no es un hecho.
2. **Corregir sin pedir permiso** (el responsable, 2026-09-29: "siempre aplica codex review hasta llegar al tope"): si el hallazgo es válido y la regla de gravedad lo pide, se corrige (si no, va a tarjeta de seguimiento y se responde su hilo), y se sigue rondando hasta 2 limpias seguidas o el tope de 8. Solo se le pregunta si contradice un ADR o una decisión suya, o al llegar al tope.
3. Aplicarla por `/orquestar` (`--en <worktree>` si el PR ya tiene uno). Los cambios de código no se hacen directo en el chat.
3b. **Hallazgo repetido más de 2 veces** (el responsable, 2026-09-29): si Codex vuelve a listar el mismo hallazgo o aviso en más de 2 rondas y el código ya lo resuelve (verificado con `grep`/`Read`), no se vuelve a tocar código: se responde en su hilo con 👍 y un par de líneas que digan por qué ya no aplica, y se sigue rondando.
4. Al subir el commit (con su sí para el push), en cada hilo de Codex: 👍 en el comentario y una respuesta de un par de líneas que diga qué se cambió y dónde, más el commit (memoria `feedback_respuesta_codex_describir_que_se_hizo`; tildes por archivo UTF-8, `-F body=@archivo`). Marcar el hilo como resuelto (`resolveReviewThread`) solo cuando esté corregido y respondido.
   **Todo este paso lo hace [`supercodex-ciclo.sh`](../scripts/supercodex-ciclo.sh)**: sube la rama, pone 👍, responde y resuelve cada hilo desde un TSV `id<TAB>respuesta.md` (las respuestas se escriben antes, a mano; el script no redacta), y dispara `@codex review` solo si quedan 0 hilos abiertos **y** cada comentario de Codex tiene respuesta nuestra y 👍 (lo audita `supercodex-atendidos.py`), con la hora `T`. Primero con `--simular`. Uso: `bash .claude/scripts/supercodex-ciclo.sh --help`.
4e. **«¿Cómo va Codex?» se responde con `python .claude/scripts/estado-prs.py [repo:prs …]`** *(2026-10-19)*: una fila por PR, contada sobre su último commit; sin argumentos, todos los abiertos de api-core y web-app.
4d. **PRs apilados: el contador solo vuelve a 0 si cambió el diff propio** *(el responsable, 2026-10-19: la cadena una funcionalidad gastó ~30 rondas en 3 vueltas)*. Tras un push que solo trajo lo propagado desde abajo, `bash .claude/scripts/rondas-vigentes.sh <repo> <pr> <sha-de-las-limpias>`: `VIGENTES` = las limpias siguen contando; `REINICIAR` = pedir 2 de nuevo. Un hallazgo nuevo en una ronda igual se atiende. Y en una pila, las rondas se piden de abajo hacia arriba: la parte N+1 recién cuando la N tiene 2 limpias.
4f. **Un tema que da vueltas sale del PR** *(el responsable, 2026-10-19)*: si la misma función o área trae hallazgos en 2 rondas seguidas, se le avisa al responsable, se crea una tarjeta nueva con los casos borde, se saca la función del PR (o se deja en su versión mínima), se responden sus hilos con 👍 remitiendo a la tarjeta y se sigue con el resto. Manda sobre «pasado el tope se sigue corrigiendo en el mismo PR».
4g. **Para no eternizar las vueltas** *(el responsable, 2026-10-19)*: (1) si el PR ya tuvo 2 limpias y la vuelta solo arregla un hallazgo puntual, basta **1 ronda limpia** sobre el commit del arreglo; (2) **bloquean solo los P1 y los P2 que afectan datos o el flujo del agente** (perder o duplicar un registro, datos de otro cliente, no poder abrir, guardar o cerrar). Los P2 de accesibilidad, foco, estados de carga o casos borde de UI se responden con 👍 remitiendo a una tarjeta de seguimiento, se resuelven y no bloquean; una ronda que solo trae esos cuenta como limpia.
4c. **Al llegar a 2 rondas limpias seguidas, se comenta en el PR, siempre y sin preguntar** *(el responsable, 2026-10-19)*: un comentario corto `✅ 2 rondas de Codex seguidas limpias sobre <sha>.` (archivo UTF-8, `--body-file`). Es la única excepción a «sin comentario resumen en el PR»: una línea, sin tabla y sin `@codex review` dentro. Si después entra un commit, el contador vuelve a 0 y el comentario se repite al volver a llegar a 2.
4b. **Todo hilo de Codex se responde, sin excepción** *(el responsable, 2026-10-01: el P2 de #<n> quedó sin atender y sin respuesta)*. No hay hilo que se quede mudo: **siempre 👍** *(el responsable, 2026-10-13: nunca 👎)*, y la respuesta dice el caso: corregido → qué cambió; no aplica o ya resuelto → por qué; fuera de alcance → el número de la tarjeta donde queda. Vale igual si el comentario llega fuera de una ronda (el responsable lo pega en el chat, o se ve al abrir el PR): se verifica, se corrige o se justifica, y se responde. **La respuesta es clara, en el mismo hilo** (reply al comentario, no un comentario suelto en el PR): en lenguaje simple, dice qué pasaba, qué se hizo y dónde (archivo y commit), o por qué no aplica; nunca solo "Corregido en <sha>" ni solo un emoji. Si hubo varias correcciones, un hilo = una respuesta propia. Antes de pasar un PR a Revisor Principal, `gh api repos/<org>/<repo>/pulls/<n>/comments` no puede dejar ningún hilo de Codex sin respuesta nuestra.
5. El contador de ese PR vuelve a 0 y sigue el ciclo.

## Cuando un PR está listo

Reportar "listo para revisión de Revisor Principal" con el PR, el commit revisado y las rondas que hicieron falta. **No mover la tarjeta.** Pasar una tarjeta a `En revisión (Revisor Principal)` solo lo hace `/trello` cuando el responsable lo pide explícitamente (regla de `CLAUDE.md`); con el PR listo, lo único que se ofrece es proponerlo.

## Cómo se reporta el estado

Cada reporte de `/supercodex` (al terminar una vuelta, al cerrar, al dejar el trabajo a medias) usa esta forma fija *(desde 2026-09-30)*. Quien lo lea debe saber **qué está hecho, qué falta y qué sigue**, sin releer la conversación:

```
Estado:
- ✅ <repo> #<n> (<rama>, commit <sha>): <qué quedó resuelto, con números>
- 🟡 <repo> #<n> (<rama>): <qué falta y por qué>
- Hilos: <X resueltos / Y abiertos> — nombrar los abiertos
- Registro: supercodex-rondas.md tiene hasta la ronda <N> de cada PR; falta anotar <cuáles>
- Siguiente paso: <una sola acción concreta>
```

- **Sin contradicciones:** o una ronda está anotada o no lo está; nunca "anotada" y "sin anotar" en el mismo mensaje. Si falta algo, va en la línea 🟡 con su nombre.
- **Con nombres:** cada rama y PR por su nombre y commit; nunca "las dos ramas".
- **Con cuentas:** cuántos hilos eran, cuántos se corrigieron, cuántos quedan y cuáles.
- **Un siguiente paso explícito**, aunque sea "esperar la ronda 3 de #<n>".

## No hace

- No comenta ni sube nada que no sea el `@codex review`, las respuestas a los hilos de Codex (corregidos, que ya no aplican o fuera de alcance) y los commits aprobados por el responsable.
- No mergea ni cambia Trello. No borra comentarios ni ramas.
- No corrige por fuera de la regla: las correcciones siguen el paso 2 de "Cuando hay hallazgos" y la regla de gravedad; los commits y el push, con el sí del responsable.

## PR en borrador hasta las 2 limpias y merge siempre manual *(el responsable, 2026-10-22)*

- Todo PR nuevo se abre con `gh pr create --draft --base develop ...`. Recién con las 2 rondas limpias seguidas sobre su HEAD (y el comentario «✅ 2 rondas…») se pasa a listo con `gh pr ready <n> -R <org>/<repo>`. Así Revisor Principal solo ve en su bandeja lo que ya pasó Codex.
- Codex revisa solo al pushear: después de un push no se pide `@codex review` a mano; `esperar-codex.py` cuenta esa revisión automática. Se pide a mano solo para la 2.ª ronda sin commit nuevo, o cuando el vigía marca una ronda perdida (30 min).
- **El merge lo aprueba Revisor Principal siempre y se hace a mano.** Nada de auto-merge ni merge sin su aprobación.

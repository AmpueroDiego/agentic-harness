---
description: Lecturas grandes y generación mecánica de archivos delegadas a un motor barato (agy/Gemini flash) en vez de gastar el contexto de Claude — inspirado en "Portal by Spotify".
argument-hint: (no se invoca con argumentos; documenta hooks y scripts que ya corren solos)
---

# /shunt

Réplica local del flujo que describe [Portal by Spotify](https://engineering.atspotify.com/2026/9/portal-by-spotify-cut-my-claude-code-token-usage-by-90): la mayoría del gasto de contexto de Claude Code no es razonar, es "leer cinco archivos para responder una pregunta sobre un método". Spotify lo resuelve con su plataforma interna (Portal) enrutando esas lecturas a un modelo barato. Acá no hay Portal, pero sí `agy` (Antigravity CLI, Gemini) ya instalado — el mismo rol, otro motor.

**No es un comando que se invoque.** Son dos hooks `PreToolUse` a nivel usuario (`~/.claude/settings.json`) que corren solos en cada sesión, más dos scripts que Claude llama cuando un hook lo bloquea. Este archivo es la referencia de qué hacen y cómo usarlos a mano si hace falta.

## Las dos piezas que bloquean (hooks)

| Hook | Dispara en | Qué bloquea |
|---|---|---|
| `check-file-size.py` | `Read` | Lectura completa de un archivo de más de `SHUNT_MIN_LINES` líneas (default 350) sin `offset`/`limit`. Una lectura acotada siempre pasa. |
| `check-bash-read.py` | `Bash` | `cat archivo` / `type archivo` sin pipe, sobre un archivo de más de `SHUNT_MIN_LINES` líneas. Con pipe (`cat x \| grep y`, `head`, `sed -n`) siempre pasa — ya está filtrado. |

Ambos escriben a stderr el comando exacto a usar y salen con código 2 (bloqueado). `SHUNT_DISABLE=1` los apaga por completo; `SHUNT_MIN_LINES=<n>` cambia el umbral.

## Las dos piezas que se invocan (scripts)

Viven en `~/.claude/scripts/` (copia real) y `.claude/scripts/` de este repo (copia versionada — mantenerlas idénticas, mismo criterio que `git-guard.sh`).

### `bulk-read.sh` — responder una pregunta sobre archivos grandes sin leerlos

```bash
bash ~/.claude/scripts/bulk-read.sh --question "¿Qué escenarios cubre este test?" --paths archivo1.cs [archivo2.cs ...]
```

No le mete el contenido del archivo al prompt — le pasa la **ruta** y `--add-dir` sobre la carpeta contenedora, y `agy` lo lee con su propia herramienta de lectura. Importante: **no se puede hacer como dice el artículo original** (envolver el contenido en tags XML dentro de `--print="..."`) porque en Windows eso choca con el límite de longitud de línea de comando a partir de ~30-60 KB — un archivo de 1200 líneas ya lo rompe (`Argument list too long`). Pasar la ruta y dejar que el propio `agy` la lea lo evita, y de paso da números de línea reales en la respuesta (el artículo dice que el worker no puede darlos de forma confiable; acá sí, porque lee el archivo real en vez de un resumen).

### `code-write.sh` — generar un archivo mecánico desde spec + referencia

```bash
bash ~/.claude/scripts/code-write.sh --spec "..." --reference archivo_referencia.cs --target archivo_nuevo.cs
```

Mismo truco: `agy` lee la referencia con `--add-dir`, no por argv. Corre en modo `plan` (solo lee/razona, no toca archivos) — el script mismo pela los fences de markdown y escribe a disco. Claude nunca ve el código generado, solo la confirmación (`Escrito: X (N líneas)`).

**No reemplaza QA/adversary.** Es un motor más dentro del reparto de coders de `/orquestar` (Step 3, tabla de motores) para el caso angosto "archivo nuevo calcado de uno existente" — el resultado sigue el mismo Step 4+ que cualquier otro coder.

**Reuso sin script nuevo, para diagramas y ADRs** *(agregado 2026-09-18)*: `code-write.sh` también sirve para dos casos que no son código C#/TS:
- **Diagramas**: `--reference <existente>.diagrama.json --target <nuevo>.diagrama.json --spec "<participantes/nodos/pasos/conexiones>"`. El `--spec` trae las decisiones de contenido reales — `agy` codifica el JSON, no decide qué muestra el diagrama. El pipeline determinista (`generar.py` → `validar.py` → `previsualizar.py` → mirar, ver [`/diagramar`](diagramar.md)) sigue obligatorio sin cambios; ahí está la verificación real, no en este script.
- **ADRs**: `--reference docs/adr/00XX-mas-parecido.md --target docs/adr/000N-slug.md --spec "<resumen de la decisión ya acordada con el responsable del repo>"`, solo después de que el responsable del repo confirme explícitamente que corresponde un ADR (gate del Step 5 de `/orquestar`, sin cambios). A diferencia del uso normal ("Claude nunca lo ve"), acá Claude **sí lee** el archivo generado antes de mostrárselo al responsable del repo — no hay QA/adversary/validador después de un ADR.

### `gh-read-shunt.sh` — leer salidas grandes de GitHub sin que entren crudas al contexto

*(agregado 2026-09-18)* Mismo patrón que `bulk-read.sh`, pero para la salida de un comando en vez de un archivo — y de hecho **la componen**, no reimplementan la llamada a `agy`: corren el comando real (subproceso de este script, nunca de `agy`, que no puede ejecutar `gh` por su cuenta), capturan la salida a un directorio temporal aislado (`mktemp -d`, no un archivo suelto en `/tmp` compartido) y se la pasan a `bulk-read.sh --paths`.

```bash
bash ~/.claude/scripts/gh-read-shunt.sh --question "¿Qué pidió cambiar el revisor?" -- pr view 42 --json comments,reviews
```

**Solo lectura, por diseño, y el script se autorrechaza si no lo es**: `gh-read-shunt.sh` acepta únicamente `pr view|pr diff|pr checks|pr status` y `api` sin `-X`/`--method`. Cualquier otro subcomando sale con error antes de ejecutar nada — ver "Qué NO se shuntea" abajo.

## Qué NO se shuntea, y por qué

- **Mutaciones del tablero de tareas** (crear/actualizar/adjuntar/comentar): la herramienta del tablero ya imprime una salida corta por diseño — la propuesta en modo simulación, la verificación en modo `--aplicar` — no el JSON crudo de la API. Pasarla por `agy` sumaría un viaje de ~60-90s sin ahorrar nada. Siguen corriendo directo. *(La herramienta del tablero y su shunt de lectura se retiraron de la versión pública; el patrón es el mismo que `gh-read-shunt.sh`.)*
- **El cuerpo de un PR**: por `orquestar.md` Step 4.7, ese texto sale del run doc de la corrida (ya corto, ya en el contexto de Claude), no del diff — no hay lectura grande que evitar ahí. Forzar una delegación leyendo el diff completo sería más caro que lo que Claude ya hace.
- **`gh pr create`/`merge`/`close`/`edit`**: nunca se delegan. Es la única escritura de este grupo sin el gate mecánico `--aplicar` que tiene el tablero, y `git-guard.sh` (el hook que exige `--base develop`) solo ve las llamadas Bash de Claude — si `agy` corriera `gh pr create` desde su propio shell, esa protección no dispara. El rechazo vive adentro de `gh-read-shunt.sh`, no en el hook.

## Historial de uso

*(mismo criterio que `antigravity.md`: se anota cada uso real para decidir con datos, no con impresiones. Vacío hasta el primer uso real.)*

| Fecha | Script | Tarea | Tamaño evitado | Tokens gastados | Veredicto |
|---|---|---|---|---|---|
| 2026-09-18 | `code-write.sh` | Relocalizar un mock-repository de 955 líneas como fixture de test (REQ-0008) | 0 (no llegó a generar nada) | ~0 | **FALLÓ** — `agy --mode plan --add-dir` intentó una herramienta que pide permiso `command(...)`, que el modo headless no puede aprobar y auto-rechaza. Sale `jetski: no output produced`, exit 1, sin escribir el target. No es un límite de tamaño ni de spec — es el primer uso real del script y pegó con un permiso no resuelto. Fallback: la tarea se mandó a Codex (`codex exec --sandbox workspace-write`), que sí puede escribir sin ese gate. Pendiente: alguien con sesión interactiva de `agy` corra `--dangerously-skip-permissions` una vez para ver si el permiso queda memorizado, o revisar qué comando interno dispara el gate antes de reintentar en headless. |

**Criterio de abandono**: si tras ~5 usos de un script el ahorro medido no es claro, dejar de usarlo para esa categoría en vez de defender la herramienta.

## Variables de entorno

| Variable | Default | Qué hace |
|---|---|---|
| `SHUNT_MIN_LINES` | `350` | Umbral de líneas para los dos hooks |
| `SHUNT_DISABLE` | (vacío) | `1` apaga los hooks |
| `SHUNT_AGY_BIN` | ruta de `agy.exe` en esta máquina | Por si el CLI se reinstala en otra ruta |
| `SHUNT_MODEL` | `gemini-3.8-flash-medium` | El nombre del modelo ya trae el esfuerzo (`-low`/`-medium`/`-high`); no combinar con `SHUNT_EFFORT` salvo que coincidan, o `agy` tira error de conflicto |
| `SHUNT_EFFORT` | (vacío, usa el del modelo) | Solo si se usa un modelo sin sufijo de esfuerzo |
| `SHUNT_TIMEOUT` | `90s` | `--print-timeout` de `agy` (necesita unidad, ej. `60s`, no `60`) |

## Lo que no hace (límites, verificados a los golpes)

- **No reemplaza una edición puntual.** Si hay que tocar una sección exacta de un archivo grande, `Read` con `offset`/`limit` pasa el hook igual — para eso está la excepción, no para `bulk-read`.
- **No delega razonamiento.** Igual que en el artículo: bugs sutiles, condiciones de carrera, decisiones de arquitectura, se quedan en Claude. `agy` acá es un lector rápido, no un revisor — para eso ya está [`/antigravity`](antigravity.md) en su rol de revisor visual, y `qa`/`adversary` en el suyo.
- **`code-write` es angosto a propósito**: un archivo nuevo o reescrito completo, con referencia. No para editar un archivo existente con historia propia en el medio.

## Relacionado

- [`orquestar.md`](orquestar.md) Step 3 — dónde encaja `code-write` en el reparto de coders.
- [`/antigravity`](antigravity.md) — el mismo CLI (`agy`), en su rol de revisor/coder visual dentro del pipeline.
- [`/codex`](codex.md) — el otro motor externo, revisor y coder mecánico.

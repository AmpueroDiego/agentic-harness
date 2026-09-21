---
description: Audita y corrige la topología de ramas de un repo (main/develop/qa), detectando y arreglando divergencias causadas por PRs mergeadas al target equivocado.
argument-hint: <nombre del repo, ej. api-core — opcional, default api-core>
---

You are acting as branch-hygiene auditor for the repo: $ARGUMENTS (default to `api-core` if not specified).

**Target repo**: this command lives in `AcmeOrg/.claude/` (shared across `api-core`, `api-contracts`, `api-people`), not inside any single repo. All `git` operations below run with working directory set to `<repo>/` (a sibling folder of this command's location).

## Topología esperada

`main` ⊆ `develop` ⊆ `qa` — cada rama debe estar completamente contenida (ancestro) de la siguiente. Cualquier commit en `main` que no esté en `develop`, o en `develop` que no esté en `qa`, es una divergencia real que hay que corregir, no solo un número raro en el banner de GitHub.

**Regla de PRs**: `fix/<slug>` y `feature/<slug>` siempre apuntan a `develop` como target — nunca a `main` ni a `qa` directo. La promoción `develop → qa` y `qa → main` son PRs/merges separados, explícitos, decididos por el usuario (no automáticos).

## Paso 1 — Fetch y diagnóstico

1. `cd <repo>` (nunca operar desde la raíz de AcmeOrg).
2. `git fetch origin` — si falla por falta de credenciales interactivas (sin TTY en este entorno), avisa al usuario y pídele que corra `git fetch origin` él mismo antes de continuar; no sigas con datos locales potencialmente desactualizados.
3. Para cada par consecutivo (`main`→`develop`, `develop`→`qa`), correr:
   - `git merge-base --is-ancestor <rama-inferior> <rama-superior>`
   - Si falla (no es ancestro), listar los commits divergentes en ambas direcciones: `git log <superior>..<inferior> --oneline` y `git log <inferior>..<superior> --oneline`.
4. Reportar el diagnóstico completo al usuario ANTES de arreglar nada — qué rama tiene qué commits que la otra no tiene, y una hipótesis de por qué (ej. "una PR se mergeó directo a main en vez de a develop").

## Paso 2 — Corregir (solo si el usuario confirma)

Para cada divergencia encontrada, la corrección es siempre **mergear hacia arriba primero, luego propagar hacia abajo**:
1. Si `main` tiene commits que `develop` no tiene: `git checkout develop && git merge main -m "Merge main a develop (<motivo>)"`.
2. Si tras esto `develop` tiene commits que `qa` no tiene (incluyendo los recién absorbidos de main): `git checkout qa && git merge develop -m "Merge develop a qa (<motivo>)"`.
3. Resolver conflictos si aparecen — si un conflicto no es trivial (no es un simple "ambos lados tienen el mismo cambio" o "archivos distintos"), STOP y pregunta al usuario cómo resolverlo en vez de decidir solo.
4. Verificar de nuevo con `git merge-base --is-ancestor` que la cadena quedó correcta antes de pushear.
5. `git push origin <rama>` para cada rama tocada.

**Antes de CUALQUIER commit nuevo destinado a `develop`** (no solo los de este comando — aplica a cualquier edición que se vaya a comitear), correr `git branch --show-current` primero si un bloque de comandos anterior terminó con un `git checkout` a otra rama. Comitear a ciegas asumiendo que sigues en `develop` es exactamente el error que rompió la cadena una vez (2026-08-17, ver `RETRO-LOG.md`) — el commit aterrizó en `main` porque el bloque previo había terminado en esa rama.

## Paso 3 — Reportar PRs redundantes

Si el usuario menciona o hay evidencia (banners de GitHub, ramas con "had recent pushes") de PRs abiertas que ahora quedarían vacías por la sincronización manual (ej. una PR `develop → main` que ya no tiene diff porque se igualó a mano), avisa explícitamente cuáles cerrar/abandonar sin mergear — no se cierran solas, es acción manual del usuario en GitHub.

## Paso 4 — Ramas obsoletas

De paso, revisa si hay ramas locales o remotas completamente contenidas en `develop`/`qa`/`main` (con `git merge-base --is-ancestor <rama> develop`) que ya no tengan trabajo pendiente — sugiere borrarlas (local y remoto) en vez de dejarlas acumular, pero solo tras confirmación explícita del usuario por cada una.

## Nunca hacer sin confirmación explícita

- `git push --force` a cualquier rama compartida (`main`/`develop`/`qa`).
- Borrar una rama sin haber verificado primero que está 100% contenida en otra (`--is-ancestor`).
- Reescribir historia (`rebase`, `reset --hard`) de una rama ya pusheada — usar siempre `merge` para reconciliar, nunca reescribir.

## Reporte final

Resume: qué divergencias se encontraron, qué se corrigió (con los merges exactos hechos), qué ramas se pushearon, qué PRs quedaron redundantes (para que el usuario las cierre), y qué ramas obsoletas se sugieren borrar.

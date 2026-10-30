---
description: Audita y corrige la topología de ramas de un repo (main/develop/qa), detectando y arreglando divergencias causadas por PRs mergeadas al target equivocado.
argument-hint: <nombre del repo, ej. api-core — opcional, default api-core>
---

You are acting as branch-hygiene auditor for the repo: $ARGUMENTS (default to `api-core` if not specified).

**Target repo**: this command lives in `AcmeOrg/.claude/` (shared across the six repos), not inside any single repo. All `git` operations below run with working directory set to `<repo>/` (a sibling folder of this command's location).

## Topología esperada

`main` ⊆ `qa` ⊆ `develop` — el flujo real es `develop` → `qa` → `main`: lo que está en `main` pasó antes por `qa`, y lo que está en `qa` por `develop`. Que `develop` vaya adelante de `qa` (y `qa` de `main`) es lo normal: son cambios aún sin promover. Divergencia real es un commit en `main` que no esté en `qa`, o en `qa` que no esté en `develop`; hay que corregirla, no es solo un número raro en el banner de GitHub.

**Regla de PRs**: `fix/<slug>` y `feature/<slug>` siempre apuntan a `develop` como target — nunca a `main` ni a `qa` directo. La promoción `develop → qa` y `qa → main` son PRs/merges separados, explícitos, decididos por el usuario (no automáticos).

## Paso 1 — Fetch y diagnóstico

1. `cd <repo>` (nunca operar desde la raíz de AcmeOrg).
2. `git fetch origin` — si falla por falta de credenciales interactivas (sin TTY en este entorno), avisa al usuario y pídele que corra `git fetch origin` él mismo antes de continuar; no sigas con datos locales potencialmente desactualizados.
3. Para cada par consecutivo (`main`→`qa`, `qa`→`develop`), correr:
   - `git merge-base --is-ancestor <rama-inferior> <rama-superior>`
   - Si falla (no es ancestro), listar los commits divergentes en ambas direcciones: `git log <superior>..<inferior> --oneline` y `git log <inferior>..<superior> --oneline`.
4. Reportar el diagnóstico completo al usuario ANTES de arreglar nada — qué rama tiene qué commits que la otra no tiene, y una hipótesis de por qué (ej. "una PR se mergeó directo a main en vez de a develop").

## Paso 2 — Proponer la corrección (solo con aprobación expresa)

Nunca mergear ni pushear directo a `main`, `qa` ni `develop`: los cambios entran por PR contra `develop` y la promoción `develop` → `qa` → `main` es del usuario. Para cada divergencia:
1. Commit en `main` que `qa` o `develop` no tienen (típico: un commit cayó directo en `main`): proponer una rama `fix/sync-main-<slug>` creada desde `develop` que traiga esos commits (`git cherry-pick <sha>`, o `git merge main` si son varios) y un PR contra `develop`. La promoción normal lo lleva luego a `qa`.
2. Commit en `qa` que `develop` no tiene: mismo tratamiento.
3. Mostrar al usuario los comandos exactos y esperar un sí antes de correrlos. Si aparece un conflicto que no es trivial (no es "ambos lados tienen el mismo cambio" ni "archivos distintos"), STOP y preguntar cómo resolverlo.
4. Tras aprobar y mergear el PR, verificar de nuevo con `git merge-base --is-ancestor` que la cadena quedó correcta.
5. Se pushea solo la rama de trabajo (`git push origin fix/sync-main-<slug>`); el PR se abre con `gh pr create --base develop`.

**Antes de CUALQUIER commit nuevo destinado a `develop`** (no solo los de este comando — aplica a cualquier edición que se vaya a comitear), correr `git branch --show-current` primero si un bloque de comandos anterior terminó con un `git checkout` a otra rama. Comitear a ciegas asumiendo que sigues en `develop` es exactamente el error que rompió la cadena una vez (ver `RETRO-LOG.md`): el commit aterrizó en `main` porque el bloque previo había terminado en esa rama.

## Paso 3 — Reportar PRs redundantes

Si el usuario menciona o hay evidencia (banners de GitHub, ramas con "had recent pushes") de PRs abiertas que ahora quedarían vacías por la sincronización manual (ej. una PR `develop → main` que ya no tiene diff porque se igualó a mano), avisa explícitamente cuáles cerrar/abandonar sin mergear — no se cierran solas, es acción manual del usuario en GitHub.

## Paso 4 — Ramas obsoletas

De paso, revisa si hay ramas locales o remotas completamente contenidas en `develop`/`qa`/`main` (con `git merge-base --is-ancestor <rama> develop`) que ya no tengan trabajo pendiente — sugiere borrarlas (local y remoto) en vez de dejarlas acumular, pero solo tras confirmación explícita del usuario por cada una.

## Nunca hacer sin confirmación explícita

- `git push --force` a cualquier rama compartida (`main`/`develop`/`qa`).
- Borrar una rama sin haber verificado primero que está 100% contenida en otra (`--is-ancestor`).
- Reescribir historia (`rebase`, `reset --hard`) de una rama ya pusheada — usar siempre `merge` para reconciliar, nunca reescribir.

## Reporte final

Resume: qué divergencias se encontraron, qué se propuso y qué se aplicó tras la aprobación (con los comandos exactos y los PRs abiertos), qué PRs quedaron redundantes (para que el usuario las cierre), y qué ramas obsoletas se sugieren borrar.

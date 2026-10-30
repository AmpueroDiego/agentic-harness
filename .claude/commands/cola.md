---
description: Cola de PRs abiertos — verifica que cada PR tenga su tarjeta de Trello y propone el orden de mergeo. Solo lectura.
argument-hint: [repo ...]
tipo: comando
fecha: 2026-10-30
tags: [pipeline, pr, revision]
---

Repos pedidos: $ARGUMENTS (si viene vacío, los seis: `api-core`, `api-contracts`, `api-people`, `api-auth`, `api-delivery`, `web-app`).

**Solo lectura.** No mueve, crea ni edita nada en Trello ni en GitHub. Si falta algo, presenta la propuesta y espera aprobación (regla de `CLAUDE.md`; lo que se escriba en Trello va por `/trello`).

## Pasos

1. **PRs abiertos** de cada repo: `gh pr list --repo <org>/<repo> --state open --json number,title,baseRefName,headRefName,mergeable,reviewRequests,files`. Si algún PR no apunta a `develop`, márcalo: es un error de flujo.
2. **Tarjeta de cada PR**, un solo comando *(retro 2026-10-27: antes se buscaba a mano y se escapaban tarjetas en `En desarrollo` con el PR abierto)*:
   ```
   python .claude/tools/pr/cola_trello.py [repo#PR ...]
   ```
   Imprime por PR `OK`, `SIN TARJETA`, `COLUMNA: <col>` (PR abierto con la tarjeta en `En desarrollo` o Backlog), `FALTA PR DE <repo>` (tarjeta «(web-app, api-core)» con el PR de un solo repo adjunto), `ARCHIVADA` o `CERRADO SIN MERGE`. Solo api-core y web-app; los otros repos, a mano con `trello.py buscar`/`ver`. Además reporta:
   - columna equivocada que el script no ve (un PR abierto y pedido a Revisor Principal va en `En revisión (Revisor Principal)` solo si el responsable ya lo pidió; antes, en `En revisión (el responsable)`);
   - tarjeta sin los miembros obligatorios (el responsable y Revisor Principal) o sin fechas, según [`ESTANDAR-ENTREGA-TRELLO-Y-GITHUB.md`](../../docs/guias/ESTANDAR-ENTREGA-TRELLO-Y-GITHUB.md);
   - reviewer `<revisor-principal>` ausente en el PR.
3. **Orden de mergeo**, dentro de cada repo:
   - primero los PRs sin dependencia entre sí; un PR que se apila sobre otro va después;
   - **si un PR parte, mueve o renombra archivos compartidos** (`git diff --name-status origin/develop...origin/<rama>` con `R` o `D`), **entra primero**; los que tocan esos archivos traen develop justo después *(retro 2026-10-27)*;
   - entre PRs que tocan los mismos archivos, el más chico primero, y avisa qué conflicto esperar en el siguiente: `bash .claude/scripts/simular-cola.sh <repo>` dice `OK` o `CONFLICTO <#PR> <rama> <archivos>` por cada PR, mergeando en cadena sobre el `origin/develop` actual;
   - entre repos: `api-auth` / `api-people` / `api-contracts` / `api-delivery` antes que `api-core`, y `api-core` antes que `web-app`, cuando un PR del front consume un endpoint nuevo.
4. **Salida**: una tabla corta — orden, repo, PR, tarjeta (enlace), columna, problemas — y debajo la lista de correcciones propuestas con el comando exacto de `/trello` para cada una, sin aplicarlas.
5. **Después de cada merge a develop**, correr `bash .claude/scripts/simular-cola.sh <repo>` sobre los PRs que quedan; cada PR que ahora choca trae develop ese mismo día, antes de la siguiente ronda de Codex *(retro 2026-10-27)*.

Sin PRs abiertos: dilo en una línea y termina.

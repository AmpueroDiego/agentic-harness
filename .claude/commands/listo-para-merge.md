---
description: Verifica que cada PR abierto esté listo para merge — hilos de Codex respondidos y resueltos, 2 rondas limpias seguidas sobre el código actual, sin conflictos y con su tarjeta. Solo lectura.
argument-hint: [repo#PR ...]
tipo: comando
fecha: 2026-10-30
tags: [harness]
---

PRs pedidos: $ARGUMENTS (si viene vacío, todos los abiertos de `api-core` y `web-app`).

**Solo lectura.** No comenta, no resuelve hilos, no mueve tarjetas. Si algo falta, lo dice y propone el siguiente paso; corregirlo va por `/orquestar`, las rondas por `/supercodex` y Trello por `/trello`. *(Skill creada el 2026-10-01, pedido del responsable: antes de pasar un PR a la sección `En revisión (Revisor Principal)` y de mergearlo hay que comprobar que quedó todo cerrado, no confiar en la memoria.)*

**Prioridad** *(el responsable, 2026-10-01)*: correrla antes de arrancar cualquier tarjeta nueva. Un PR con hilos sin responder, sin resolver o sin sus 2 rondas limpias se cierra primero; lo nuevo espera.

## Cuándo un PR está listo

Los cinco, sin excepción:

1. **Apunta a `develop`**, sin conflictos y sin ser borrador.
2. **Cada hilo de Codex tiene respuesta nuestra** (clara, en el mismo hilo; regla 4b de [`/supercodex`](supercodex.md)).
3. **Cada hilo de Codex está resuelto.** Ninguno abierto.
4. **Las 2 últimas rondas de `@codex review` son limpias** (sin hallazgos en línea ni en el review, security review sin problemas) y **la última revisó el HEAD actual**: un commit nuevo después de una ronda limpia obliga a otra ronda.
5. **Tiene tarjeta de Trello** con el PR adjunto, y su orden en la cola de merges no choca con los PRs de adelante.

## Pasos

1. **GitHub (puntos 1 a 4)**, un solo comando:
   ```
   python .claude/tools/pr/listo_para_merge.py [repo#PR ...]
   ```
   Imprime por PR `LISTO` o `NO LISTO` con cada motivo (conflictos, hilos sin respuesta, hilos sin resolver, rondas limpias seguidas, ronda que no cubre el HEAD). No hay que repetir esas consultas a mano.
2. **Cola y tarjeta (punto 5)**: `python .claude/tools/pr/cola_trello.py [repo#PR ...]` verifica que cada PR tenga su tarjeta, en qué columna está y, en las tarjetas de dos repos, que tenga adjunto el PR de ambos; cualquier línea distinta de `OK` deja el PR `NO LISTO`. El orden de mergeo lo propone [`/cola`](cola.md).
3. **Conflictos de verdad**: `bash .claude/scripts/simular-cola.sh <repo>` simula con `git merge-tree` cada PR abierto contra los de adelante (lo mismo que el paso 7b de [`/worktree sincronizar`](worktree.md)); un `CONFLICTO` deja el PR `NO LISTO`. Un PR que choca con otro de la cola se resuelve en la rama nueva antes de llegar a Revisor Principal.
4. **Entregar el resumen**: una tabla `PR | estado | qué falta`, con el conteo `X/Y listos`. Nombrar cada PR que falte con su motivo; nunca decir "todo OK" sin haber corrido el script en esa misma vuelta.

## Qué hacer con cada motivo

| Motivo | Siguiente paso |
|---|---|
| Hilo sin respuesta o sin resolver | verificar el hallazgo, corregir por `/orquestar --en`, responder y resolver (`/supercodex`, regla 4b) |
| Menos de 2 rondas limpias, o la última no cubre el HEAD | pedir `@codex review` (`/supercodex`) |
| Conflictos | `/worktree sincronizar <repo>--<slug>` y resolverlos en la rama |
| Sin tarjeta o sin PR adjunto | `/trello adjuntar` (propuesta primero) |
| Rama sin `/codex` local previo | correr [`/codex`](codex.md) en el worktree y corregir antes de seguir |

## Lo que no hace

- Excluye los PRs que el responsable dejó fuera de la cola (lista `EXCLUIDOS` en el script). Pedido explícito de un PR (`repo#PR`) sí lo evalúa.
- No decide pasar la tarjeta a `En revisión (Revisor Principal)`: eso lo pidel responsable explícitamente (guía de entrega, sección 2). Esta skill solo dice si ya se puede.
- No cuenta como limpia una ronda que Codex no terminó (~10 min sin respuesta se informa tal cual).
- Un PR de otro repo (`api-contracts`, `api-people`...) no se revisa con Codex: se excluye, igual que en `/supercodex`.

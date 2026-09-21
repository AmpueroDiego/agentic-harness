---
description: Audita la salud del vault de Obsidian — grafo de enlaces, grupos de color, exclusiones y junctions — y propone correcciones sin aplicar ninguna.
---

# /auditar-vault

Revisa que el vault siga siendo navegable y que su configuración coincida con la
realidad. **Reporta y propone; no toca nada.** Igual que `retro` y `system-auditor`,
y coherente con la regla de cero eliminaciones de `CLAUDE.md`.

## Por qué existe

El 2026-09-09 el vault tenía **57 nodos huérfanos y 59 islas**, y ni el hook ni
nadie lo había notado. Ninguno de esos fallos era de contenido:

| Causa | Efecto |
|---|---|
| Un filtro que escondía todos los `README.md` | 26 notas huérfanas: sus índices dejaron de indexarse |
| El `.venv` de `scripts/agentes-ia` dentro del vault | 42 notas basura de numpy, httpx, chromadb |
| Dos grupos de color apuntando a carpetas borradas | Contextos que parecían tener color y salían grises |
| `api-delivery` sin grupo desde que se clonó | El único de los 6 repos sin color |
| Tarjetas con 1 enlace entrante y 0 salientes | Se dibujaban lejos y parecían una isla |

La lección: **casi siempre el problema es de configuración, no de enlaces.**
Antes de agregar wikilinks a mano, revisar exclusiones y grupos.

## Herramientas

En `.claude/tools/vault/`, Python 3 sin dependencias — misma convención que
`.claude/tools/drawio/`.

| Archivo | Qué responde |
|---|---|
| `grafo.py` | ¿Está el grafo en una pieza? ¿Hay huérfanos, hojas colgando de un hilo, enlaces rotos? |
| `obsidian.py` | ¿La config coincide con el disco? Grupos muertos, carpetas grises, colores repetidos, junctions y exclusiones peligrosas |

## El ciclo

```bash
python .claude/tools/vault/grafo.py --detalle
python .claude/tools/vault/obsidian.py
```

Luego, si algo aparece, seguir este orden — **de la causa más barata a la más cara**:

### 1. ¿Es una exclusión?

Mirar la sección EXCLUSIONES de `obsidian.py`. Un filtro por nombre de archivo
(`README.md`, `INDEX`) es el sospechoso número uno: si esconde una nota índice,
deja huérfano todo lo que colgaba de ella. **Una línea de configuración puede
producir decenas de huérfanas.** Se arregla en `.obsidian/app.json` o en
`Settings → Files & Links → Excluded files`.

### 2. ¿Es un junction que falta?

Obsidian no indexa carpetas que empiezan con punto. Si los enlaces a
`agentes-pipeline/` o `comandos-pipeline/` salen en rojo, el junction no existe
en esta máquina. `obsidian.py` imprime el comando exacto para recrearlo.

### 3. ¿Es un grupo de color desfasado?

Grupos que no matchean nada = carpeta movida o borrada. Carpetas sin grupo =
nodos grises. Se corrige en la pestaña **Groups** del Graph View.

### 4. Recién ahora, ¿faltan enlaces?

Si la nota es contenido real y nadie la enlaza, hay dos arreglos y no son
equivalentes:

- **Indexarla** donde corresponda (`contexto-negocio/README`, `docs/adr/README`…).
  Le da un enlace entrante.
- **Darle una barra de navegación** arriba. Le da enlaces salientes.

Las **hojas** que reporta `--detalle` (entrantes pero ningún saliente) merecen la
segunda: cuelgan de un solo hilo y si su índice se oculta vuelven a quedar sueltas.
Es lo que pasó con las 13 tarjetas de Trello.

## Reglas al aplicar correcciones

1. **Nunca borrar una nota** para "limpiar" el grafo. Si sobra, se excluye de
   Obsidian; el archivo se queda. Vale doble si vive en un repo de la
   organización, donde quitarla exigiría un PR contra `develop`.
2. **No enlazar por enlazar.** Un enlace inventado entre notas que no tienen que
   ver ensucia el grafo más de lo que lo arregla. Si una nota no tiene con qué
   relacionarse, dejarla suelta y decirlo.
3. **Cero pipes escapados** en wikilinks (regla 13 del Playbook). Eso descarta los
   wikilinks con alias dentro de tablas markdown: usar listas.
4. **Antes de tocar un archivo, `git status`.** Si otra sesión lo tiene modificado,
   no editarlo: avisar. Y nunca `git commit` a secas — usar `git commit -- <ruta>`,
   que no arrastra lo que otro dejó en el staging.

## Al terminar

Actualizar [`Meta/Graph-View-Config.md`](../../Meta/Graph-View-Config.md) con los
números reales. **`.obsidian/` está en el `.gitignore`**: esa nota es la única
forma de reconstruir grupos, fuerzas y exclusiones en otra máquina. Si se cambian
desde la interfaz y no se anotan ahí, se pierden — ya pasó: la nota declaraba 13
grupos cuando había 21, y tres juegos distintos de valores de fuerzas.

Si el cambio da para lección permanente, va al Playbook. Si es una tarea
pendiente, va a `TASKS.md`. No son lo mismo: el Playbook evita que vuelva a
pasar, `TASKS.md` arregla lo que ya pasó.

## Qué NO cubre

El chequeo barato de cada commit lo hace `scripts/validar-vault.py` desde el hook
`pre-commit`: codificación, pipes escapados, enlaces rotos y **huérfanos**. Esta
skill es la revisión profunda que ese hook no puede hacer — sobre todo la
configuración de Obsidian, que ni siquiera está en git.

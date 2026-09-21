---
tipo: meta
tags: [meta, obsidian, graph-view]
---

# 🕸️ Guía de configuración — Separación de contextos en Graph View

> [!info] Objetivo
> Que el Graph View muestre **islas separadas por repo/contexto** (`api-core`, `api-contracts`, `api-people`, y dentro de `api-core`: agentes / ADRs / runs / contexto-negocio / mockups) en vez de una maraña única.

Este vault ya trae aplicado el primer enfoque (colores por grupo, en `.obsidian/graph.json`) — esta nota documenta por qué, para poder ajustarlo después.

---

## 1. Separación física — pestaña `Forces`

> [!tip] Valores reales, leídos de `.obsidian/graph.json` el 2026-09-09
> | Parámetro | Valor | Efecto |
> |---|---|---|
> | **Center force** | `0.15` | Baja la atracción hacia el centro; evita que todo se apelotone en un punto. |
> | **Link force** | `0.8` | Nodos conectados (mismo contexto) se atraen y forman clústeres. |
> | **Repel force** | `16` | Los clústeres se empujan entre sí y no se superponen. |
> | **Link distance** | `180` | Espacio suficiente para leer los títulos de los nodos conectados. |
>
> Los valores que figuraban antes acá (`0.12` / `0.9` / `13` / `195`) y los del checklist del final (`0.05` / `0.6` / `20` / `260`) **no coincidían entre sí ni con el archivo**. Se ajustan a mano desde la pestaña Forces y nadie volvió a anotarlos; la tabla de arriba es la que se leyó del archivo.

> [!info] Un clúster que se ve apartado no siempre está desconectado
> Si un grupo de notas aparece flotando lejos, antes de agregar enlaces conviene mirar **cuántos enlaces salientes** tienen. Un abanico de nodos que cuelga de un solo índice, con 1 entrante y 0 salientes cada uno, se dibuja lejos aunque esté conectado. Pasó con las 13 tarjetas de `docs/trello` el 2026-09-09: se resolvió dándoles navegación de vuelta, no tocando las fuerzas.

---

## 2. Separación visual — pestaña `Groups`

> [!warning] Actualizado 2026-08-17 tras la migración a `agentic-harness`
> `.claude/agents` y `contexto-negocio` (con su subcarpeta `legacy-erd/`) se movieron de `api-core/` a la raíz del vault ese día. Las rutas de abajo ya reflejan la ubicación nueva — si algún día vuelven a moverse, actualizar aquí también o los grupos de color dejan de matchear (los nodos afectados salen grises, sin color).

> [!info] Subcategorización por tag (2026-08-17)
> Dentro de `docs/runs`, los tags `#feature` (corridas que entregaron funcionalidad nueva) y `#mantenimiento` (refactors, config, housekeeping) tienen su propio color, evaluados **antes** que el grupo por carpeta — así una corrida de mantenimiento (habilitar Swagger en QA) se ve distinta de una de feature (un endpoint nuevo), sin dejar de estar dentro del clúster general de `runs`.

> [!success] Auditado y corregido el 2026-09-09
> La lista de abajo **se verificó grupo por grupo contra los archivos reales**: cada `query` matchea algo y ninguna carpeta con notas quedó sin color. Antes de esa auditoría esta sección decía "13 grupos (2 por tag, 11 por ruta)" cuando había 21, dos de ellos apuntando a carpetas inexistentes.

**25 grupos: 3 por `tag`, 18 por `path`, 4 por `file`.** El único campo de frontmatter que hace falta es `tags`, que las corridas ya usan.

> [!danger] Cerrar Obsidian antes de editar `.obsidian/graph.json` a mano
> Obsidian guarda la configuración del grafo en memoria y la **reescribe entera** en `graph.json` con cualquier cambio de la vista, incluso un zoom (la clave `scale` vive en ese archivo). Si se edita el archivo con Obsidian abierto, lo pisa.
>
> Pasó: el arreglo del 2026-09-09 quedó anotado acá, pero el 2026-09-10 `graph.json` tenía otra vez los 21 grupos viejos, con `web-app-secondary` y `mockups` incluidos. Si se cambia desde la interfaz (pestaña **Groups**) no hay riesgo; si se cambia el archivo, primero cerrar Obsidian.

> [!info] El orden importa: gana el primer grupo que matchea
> `path:` busca **dentro** de la ruta, así que `path:"web-app"` también pinta `web-app-legacy/`. Por eso el grupo del legacy va **antes** que el de `web-app`, igual que un grupo más específico va antes que el general.

### 🟣 Violeta `#7C3AED` — el sistema agéntico
- `agentes-pipeline` — los 10 agentes (`.claude/agents/` vía junction)
- `comandos-pipeline` — los 7 comandos (`.claude/commands/` vía junction) *(agregado 2026-09-09)*
- `docs/runs` — historial de corridas y prompts en la raíz del vault *(agregado 2026-09-09)*
- `Meta` — documentación del propio vault y del sistema multiagente

### 🟪 Lila `#C084FC` — gobernanza, guías y tablero de mando
- `docs/adr` · `docs/guias` · `docs/pruebas`
- `file:AGENTS` · `file:CLAUDE` · `file:TASKS` · `file:Home` *(Home agregado 2026-09-09)*

### 🟢 Verde `#10B981` — `contexto-negocio`
Esquemas de BD, reglas de negocio e insumos transversales. Incluye `legacy-erd/`, `diagramas/` e `historico/`.

### 🟠 Naranja `#F97316` — `docs/trello`
Las 13 tarjetas del tablero más su índice.

### 🔷 Cian `#06B5D4` — los repos de código
- `api-core` · `web-app` · `api-contracts` · `api-people` · `api-auth` · `api-delivery` *(api-delivery agregado 2026-09-09: era el único de los 6 sin color)*

### 🟤 Ámbar oscuro `#B45309` — `web-app-legacy`
El CRM web anterior (VB.NET WebForms, repo `AcmeLegacyOrg/web-app`). Color propio para no confundirlo con el `web-app` React, que es cian. *(Agregado 2026-09-10.)*

### 🟣 Fucsia `#D946EF` — `scripts`
El pipeline LangGraph de `scripts/agentes-ia`. Color propio a propósito: es una **línea paralela y experimental**, no parte del pipeline productivo violeta. *(Agregado 2026-09-09.)*

### Por tag, evaluados antes que la ruta
- 🔵 `#feature` `#3B81F6` · 🔴 `#fix` `#FB7185` · 🟡 `#mantenimiento` `#FACC15`

> [!note] `#fix` y `#mantenimiento` compartían el mismo rosa
> Hasta el 2026-09-09 los dos usaban `#FB7185` — dos grupos distintos que se veían idénticos. `#mantenimiento` pasó a amarillo.

> [!warning] Grupos eliminados el 2026-09-09 por no matchear nada
> - `web-app-secondary` — la carpeta se borró (era un worktree de `web-app`, no un proyecto).
> - `docs/mockups` — esa carpeta **no existe**; el grupo llevaba tiempo apuntando al vacío. *(corregido 2026-09-11: la carpeta sí existe, pero solo tiene `.html`; el grupo no pintaba nada porque no hay `.md` que Obsidian indexe ahí, así que quitarlo sigue siendo correcto.)*
>
> Un grupo que no matchea no rompe nada, pero ensucia la pestaña Groups y hace creer que un contexto tiene color cuando en realidad sale gris.

> [!tip] Lo único que queda gris a propósito
> El `README.md` de la raíz. Un grupo `file:README` matchearía **todos** los README del vault, incluidos los de los repos de código, y les robaría su color cian. Un nodo gris es mejor que seis mal pintados.

> [!tip] Por qué por ruta y no por tag
> Los archivos de `.claude/agents/*.md` ya tienen su propio frontmatter (`name`, `description`, `tools`, `model`) consumido por Claude Code — agregarles tags de Obsidian arriba es innecesario y evitable. Agrupar por `path:` logra la misma separación visual sin tocar esos archivos.

---

## 2.5. Exclusiones — `Settings → Files & Links → Excluded files`

> [!warning] Una exclusión demasiado amplia rompe el grafo sin que se note
> Esa pantalla escribe en `userIgnoreFilters` de `.obsidian/app.json` — la lista y el archivo son lo mismo. Lo que se excluye **desaparece del grafo, de la búsqueda y del autocompletado**, y todo lo que colgaba de ello queda huérfano.

Estado al 2026-09-09, con el motivo de cada una:

| Filtro | Por qué |
| :--- | :--- |
| `node_modules` | Dependencias de npm |
| `bin`, `obj`, `dist`, `build`, `.vs` | Artefactos de compilación |
| `.venv` | **Agregado el 2026-09-09.** El entorno virtual de `scripts/agentes-ia` metía **42 notas huérfanas** en el grafo: los `LICENSE.md` y `README.md` de numpy, httpx, chromadb, huggingface… Era la causa de las tres cuartas partes de los nodos sueltos |
| `.claude/worktrees` | Redundante hoy (Obsidian ya ignora carpetas con punto), pero explícito: **un worktree es una copia completa del vault** y duplicaría cada nota si alguna vez se moviera fuera de `.claude/` |
| `docs/.obsidian` | Config de un vault anidado viejo. *(2026-09-11: la carpeta ya no existe; el filtro no excluye nada)* |
| `api-people/README.md` | Archivo de una línea (`# BackEndCore 8`), resto de la plantilla del repo. Se excluye en vez de borrarlo: el archivo vive en el repo de la organización y quitarlo exigiría un PR contra `develop` |

> [!danger] El filtro que había y se quitó: `README.md`
> Hasta el 2026-09-09 la lista excluía **todos** los `README.md`. Parecía inofensivo —tapaba el ruido de los repos— pero escondía los índices del propio vault: `contexto-negocio/README`, `docs/adr/README`, `docs/trello/README`, `docs/pruebas/README`.
>
> Efecto en cascada: las 13 tarjetas de Trello, las 8 notas de `web-app/docs/review` y varias más **sólo tenían enlace entrante desde su índice**. Con el índice oculto quedaban flotando. Eran **26 nodos huérfanos** producidos por una sola línea de configuración.
>
> Se quitó, y con `node_modules` y `.venv` ya filtrados dejó de hacer falta. **Lección:** antes de excluir un patrón por nombre de archivo, revisar si ese nombre lo usan también las notas índice del vault.

---

## 3. El problema de los nodos índice (`Home`, `INDEX`)

> [!warning] Por qué rompen la separación
> `Home.md` (el dashboard raíz) y `runs/INDEX.md` enlazan a *todo*. Actúan como anclas centrales que tiran de todos los clústeres hacia un mismo punto.

> [!tip] Truco: ocultarlas temporalmente
> En la pestaña **Filters** del Graph View, escribe:
> ```
> -file:Home -file:INDEX
> ```
> Con los índices ocultos, los contextos se separan en **islas flotantes reales**. Reactiva el filtro cuando quieras volver a ver el mapa completo con sus conectores.

---

## 4. `.claude/` no se indexa — Obsidian ignora carpetas con punto

> [!warning] Descubierto 2026-08-17
> Obsidian no escanea ninguna carpeta que empiece con `.` (no es exclusivo de `.obsidian`/`.git`) — así que `.claude/agents` y `.claude/commands` nunca aparecen en el Graph View ni son visibles para Dataview, aunque el contenido esté ahí y sea markdown válido. No es un bug de la consulta (`FROM ".claude/agents"` daba "No results to show").

> [!tip] Solución: junction de Windows (Mac/Linux: symlink)
> Un junction/symlink hace que Obsidian vea los mismos archivos bajo un nombre sin punto, sin duplicar nada ni afectar a Claude Code (que sigue usando `.claude/` normalmente, sin enterarse del junction).
>
> **Ya existe uno creado:** `AcmeOrg/agentes-pipeline/` → `.claude/agents/`. Es local (está en `.gitignore`, no se versiona) — si clonas este repo en otra máquina, hay que recrearlo:
> ```powershell
> New-Item -ItemType Junction -Path "agentes-pipeline" -Target ".claude\agents"
> ```
> En Mac/Linux, el equivalente es un symlink:
> ```bash
> ln -s .claude/agents agentes-pipeline
> ```
> Si en el futuro se quiere indexar también `.claude/commands` (`orquestar.md`, `verificar-ramas.md`), el mismo truco aplica con otro nombre de carpeta destino.

> [!todo] Pendiente: junction para `.claude/commands/` (definido 2026-09-09)
> *(corregido 2026-09-11: ya no está pendiente — `comandos-pipeline/` existe desde el 2026-09-09 y el grupo `path:"comandos-pipeline"` ya está en `graph.json`. Hoy son más: se sumaron `auditar-vault` y `worktree`, entre otros.)*
> Los 4 comandos (`orquestar.md`, `levantar-proyecto.md`, `verificar-ramas.md` y `diagramar.md`, agregado el 2026-09-09) siguen siendo los últimos nodos fuera del grafo. El nombre acordado es **`comandos-pipeline/`** y ya está en `.gitignore`; falta crear el junction en el checkout principal:
> ```powershell
> New-Item -ItemType Junction -Path "comandos-pipeline" -Target ".claude\commands"
> ```
> ```bash
> ln -s .claude/commands comandos-pipeline   # Mac/Linux
> ```
> Mientras no exista, los enlaces `[[comandos-pipeline/...]]` de [[sistema-multiagente-supervisado|Sistema Multiagente Supervisado]] salen en rojo. Al crearlo, agregar también el grupo de color `path:comandos-pipeline` en la pestaña **Groups** (sección 2), o esos nodos quedan grises.

---

## 5. Por qué el hook pre-commit se queja de `agentes-pipeline/` dentro de un worktree

> [!warning] Falso positivo conocido (2026-09-09)
> El validador de integridad del vault (`pre-commit`) reporta los enlaces `[[agentes-pipeline/*]]` y `[[comandos-pipeline/*]]` como **no resueltos** cuando el commit se hace desde un worktree de `.claude/worktrees/`. No es un error real.
>
> La cadena es: el junction está en `.gitignore` (correcto, es un atajo local que se recrea por máquina) → git no lo versiona → **un worktree, que es un checkout limpio de lo que git tiene, no lo trae** → el hook busca la carpeta ahí, no la encuentra, y avisa.
>
> Obsidian nunca abre el worktree: abre el checkout principal, donde el junction sí existe y los enlaces resuelven bien. La advertencia no bloquea el commit (`⚠️`, no `❌`). Si llega a molestar, el hook puede saltear los enlaces que empiezan con `agentes-pipeline/` o `comandos-pipeline/` cuando detecta que corre dentro de `.claude/worktrees/`.
>
> *(corregido 2026-09-11: el aviso ya no sale, pero por una razón peor. Desde el commit `9cce20a` (2026-09-09) `validar-vault.py` saltea toda carpeta cuya ruta contenga `worktrees` (`IGNORE_DIRS`), y dentro de un worktree la raíz misma la contiene: **escanea 0 notas y no valida nada**. Un commit hecho desde un worktree pasa el hook sin revisión real; validar desde el checkout principal.)*

---

## Checklist rápido

Estado verificado el **2026-09-09** contra `.obsidian/graph.json` y contra los archivos reales del vault.

- [x] Fuerzas: `Center 0.15` · `Repel 16` · `Link force 0.8` · `Link distance 180` — ver la tabla de la sección 1, que es la que se leyó del archivo
- [x] **25 grupos de color**: 3 por `tag:` (evaluados primero) + 18 por `path:` + 4 por `file:`. Todos matchean al menos un archivo *(2026-09-10: se sumó `web-app-legacy`, y se reaplicaron los cambios del 09-09 que Obsidian había pisado)*
- [x] Ninguna carpeta con notas quedó gris, salvo el `README.md` de la raíz, a propósito (ver sección 2)
- [x] Junction `agentes-pipeline/` → `.claude/agents/` — los 10 agentes indexados
- [x] Junction `comandos-pipeline/` → `.claude/commands/` — los 7 comandos indexados *(creado 2026-09-09)*
- [x] Exclusiones al día: `.venv` fuera, filtro global de `README.md` retirado (ver sección 2.5)
- [x] **Grafo en una sola pieza**: 181 notas indexadas, 0 nodos aislados *(se partió de 59 islas y 57 aislados; verificado de nuevo el 2026-09-10)*
- [ ] Filtro `-file:Home -file:INDEX` — actívalo manualmente cuando quieras ver clústeres separados (no es permanente a propósito)

> [!warning] Esta configuración **no se versiona**
> `.obsidian/` está en el `.gitignore`, así que los grupos, las fuerzas y las exclusiones viven sólo en esta máquina. Esta nota es la única forma de reconstruirlos en un clon nuevo — si se cambian desde la interfaz y no se anotan acá, se pierden. Es exactamente lo que pasó con los números que había antes: tres juegos de valores distintos, ninguno igual al archivo.

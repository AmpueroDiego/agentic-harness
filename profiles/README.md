# Perfiles de stack

Un perfil describe, para un lenguaje/framework concreto, lo que los agentes
`coder`/`coder-ui` necesitan saber para escribir código consistente en ese
repo: capas, comandos de build/test/lint, convenciones de nombres, y
"hard rules" nacidas de bugs reales (no genéricas — cada regla debería
poder señalar el problema que evita).

El harness trae tres de ejemplo (`dotnet.md`, `node-ts.md`, `python.md`).
No son un catálogo cerrado: son el punto de partida para escribir el tuyo.

## Cómo se usa

1. En `harness.ini`, cada `[repo:<id>]` declara `stack_profile = <nombre>`
   (el nombre de archivo sin `.md`, dentro de esta carpeta).
2. El instalador copia el contenido del perfil dentro del agente `coder`
   (backend) o `coder-ui` (frontend) del repo destino, en la sección
   `## Stack real` que ambos agentes traen vacía por defecto.
3. Si tu stack no está entre los tres de ejemplo (Go, Java/Spring, Rails...),
   copia `_plantilla.md`, complétalo con tu stack real y referencia ese
   archivo en `harness.ini`.

## Qué va en un perfil, y qué no

Va: comandos reales (`npm run test`, no "corré los tests"), estructura de
carpetas real, la lista de "hard rules" con el bug que las originó.

No va: reglas de negocio, nombres de servicios internos, ni nada específico
de un cliente — eso vive en la sección "Visión de dominio" de `CLAUDE.md`
del proyecto, no en el perfil de stack. Un perfil debería poder compartirse
entre dos proyectos distintos que usan el mismo stack.

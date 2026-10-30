---
tipo: comando
fecha: 2026-10-30
tags: [trello, entregas]
description: Opera el tablero Trello dominio (crear, mover, fechar, asignar, adjuntar el PR) con propuesta previa obligatoria y verificación después de escribir. Reemplaza a scripts/trello.ps1.
argument-hint: (qué hacer en el tablero, ej. "crear tarjeta para X" o "pasar la tarjeta del PR #<n> a revisión")
---

# /trello

Toda operación sobre el tablero **dominio** pasa por `.claude/tools/trello/trello.py`. No escribas Python suelto contra la API ni uses `scripts/trello.ps1`: en esta máquina no conecta (schannel), y el script nuevo ya resuelve nombres contra el tablero vivo, aplica las reglas del equipo y relee cada cambio.

Las reglas de fondo —qué campos lleva una entrega, el límite de la descripción, a qué columna va un PR— **no están acá**: su dueña es [`docs/guias/ESTANDAR-ENTREGA-TRELLO-Y-GITHUB.md`](../../docs/guias/ESTANDAR-ENTREGA-TRELLO-Y-GITHUB.md). Leela antes de proponer una entrega. Si esta skill y la guía dicen cosas distintas, manda la guía y esta skill se corrige.

Para revisar de una vez qué PR abiertos tienen tarjeta y en qué orden mergearlos, usa [`/cola`](cola.md) (solo lectura).

## Ciclo

1. **Leer el tablero vivo.** Nunca `docs/trello/`, que es un export con fecha.
   ```
   python .claude/tools/trello/trello.py tablero
   python .claude/tools/trello/trello.py buscar "palabras del título"
   python .claude/tools/trello/trello.py listar --columna Backlog [--desc]
   python .claude/tools/trello/trello.py ver <shortLink|URL>
   ```
   **Si la salida va a ser grande** (`buscar` con muchos candidatos, `listar --desc` de una columna larga, `tablero` completo, `ver` de una tarjeta con descripción larga), usar `trello-read-shunt.sh` en vez de correr `trello.py` directo — no entra crudo al contexto de Claude, `agy` lo lee y responde la pregunta puntual *(agregado 2026-09-18, ver [`/shunt`](shunt.md))*:
   ```
   bash ~/.claude/scripts/trello-read-shunt.sh --question "¿Qué tarjetas de 'En curso' tocan api-core?" -- buscar api-core
   ```
   Esto es solo para las cuatro lecturas de arriba. Las mutaciones del paso 2 **no** pasan por acá: su salida ya es corta por diseño (ver más abajo).
2. **Simular.** Sin `--aplicar`, `crear`, `actualizar`, `adjuntar`, `quitar-adjunto`, `comentar` y `ordenar` no envían nada: imprimen la propuesta exacta, con nombres ya resueltos, largo de la descripción y tarjetas parecidas.
3. **Mostrar la propuesta al usuario y esperar aprobación expresa.** Es obligatorio (CLAUDE.md y sección 1 de la guía). Si pide cambios, se corrige y se vuelve a simular.
4. **Aplicar** el mismo comando con `--aplicar`. El script relee la tarjeta y compara campo por campo; si dice `VERIFICACION FALLIDA`, se informa tal cual, no se da por hecho.

## Comandos

```
python .claude/tools/trello/trello.py crear --columna Backlog --titulo "<título del PR o tarea> (<repo>)" \
    --desc-archivo desc.md --etiqueta Frontend --miembro <responsable> [--inicio AAAA-MM-DD] [--vence AAAA-MM-DD]

python .claude/tools/trello/trello.py actualizar <tarjeta> [--columna "En revisión (Revisor Principal)"] [--desc-archivo desc.md] \
    [--etiqueta Backend] [--miembro "Revisor Principal"] [--inicio AAAA-MM-DD] [--vence AAAA-MM-DD]

# Renombrar una tarjeta EXISTENTE es una excepcion puntual (seccion 1 de la guia), no una operacion de rutina:
# requiere --titulo Y --confirmo-renombrar, y solo se usa cuando el responsable lo pide explicitamente para esa tarjeta.
python .claude/tools/trello/trello.py actualizar <tarjeta> --titulo "<titulo nuevo>" --confirmo-renombrar

# Archivar (reversible; NO elimina): la tarjeta sale del tablero y se restaura desde "Elementos archivados". Solo si el responsable lo pide.
python .claude/tools/trello/trello.py actualizar <tarjeta> --archivar

python .claude/tools/trello/trello.py adjuntar <tarjeta> --url https://github.com/<org>/<repo>/pull/<n> --nombre "#<n> <título del PR>"
python .claude/tools/trello/trello.py adjuntar <tarjeta> --archivo ruta/al/script.sql

# Quitar un adjunto es borrar: solo con el OK del responsable. Por URL exacta, y relee la tarjeta para verificar.
python .claude/tools/trello/trello.py quitar-adjunto <tarjeta> --url https://github.com/<org>/<repo>/pull/<n>

python .claude/tools/trello/trello.py comentar <tarjeta> --texto-archivo comentario.md

python .claude/tools/trello/trello.py ordenar --columna Backlog --orden-archivo orden.txt
```

- **`ordenar`** reordena una columna entera: el archivo lleva un shortLink o URL por línea, de arriba hacia abajo. Así se prioriza el Backlog: P1 arriba, después P2 y al final P3. La prioridad es solo la posición, sin etiquetas (decisión del responsable).

- **Descripción y comentarios siempre desde un archivo UTF-8** en el scratchpad, nunca como argumento: en la consola de Windows las tildes se corrompen.
- `<tarjeta>` acepta el shortLink (`<card-id>`), la URL o el id.
- Columnas, etiquetas y miembros van por nombre, sin importar mayúsculas ni tildes. Si un nombre es ambiguo, el script se detiene y lista las opciones: `"En revisión"` coincide con dos columnas.

## Lo que el script impide

| Regla | Cómo |
|---|---|
| El título de una tarjeta existente no se toca por rutina | `actualizar --titulo` exige además `--confirmo-renombrar`; sin el responsable pidiéndolo explícito para esa tarjeta puntual, no se usa (sección 1 de la guía) |
| Entregar a revisión sin fechas | `actualizar --columna "En revisión (...)"` falla si la tarjeta no tiene (o el mismo comando no trae) `--inicio` y `--vence` (desde 2026-10-02: se pasaron 4 tarjetas a revisión sin fechas) |
| Entregar a revisión sin el responsable y Revisor Principal de miembros | `actualizar --columna "En revisión (...)"` falla si a la tarjeta (sumando los `--miembro` del mismo comando) le falta `<responsable>` o `<revisor-principal>` (el responsable, 21/10) |
| Cero eliminaciones | No hay acción para borrar tarjetas, etiquetas, miembros ni adjuntos; `actualizar` solo suma (y `--archivar` solo oculta, se puede restaurar) |
| Descripción de 560 caracteres como máximo | `crear` y `actualizar` fallan si se pasa |
| El revisor principal se resuelve por su rol configurado | `--miembro "Revisor Principal"` resuelve a `<revisor-principal>` |
| Sin comentarios con enlaces de PR | `comentar` falla; el PR va con `adjuntar` |
| Orden a medias | `ordenar` se detiene si el archivo no lista cada tarjeta de la columna exactamente una vez; después relee la columna y compara la secuencia |
| Sin duplicados | `crear --aplicar` se detiene si hay tarjetas parecidas, salvo `--aunque-exista` tras confirmarlo con el usuario |

## Lo que decide el usuario, no el script

- **Cuándo pasa una tarjeta a revisión.** Solo cuando el responsable lo pide explícitamente; abrir el PR no alcanza (regla en la sección 2 de la guía). Con el PR abierto, lo único que se ofrece es `adjuntar --url`.
- **Miembros y fechas de una tarea en Backlog.** Los miembros y fechas obligatorios de la guía aplican cuando la tarjeta se **entrega a revisión**. Para una tarea nueva en Backlog, proponé y dejá que el usuario ajuste: una tarea nueva puede crearse sin Revisor Principal.
- **Si una tarea ya tiene tarjeta.** Preguntalo al inicio (sección 0 de la guía), usando `buscar` para ofrecer candidatas.

## Entorno

Credenciales en `~/.trello-credentials.json` (`apiKey`, `token`, `defaultBoardId`), guardado con BOM; el script ya lo lee con `utf-8-sig`. El script no exporta a `docs/trello/`: ese export se desactualiza y la guía prohíbe operar con él.

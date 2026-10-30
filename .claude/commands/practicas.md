---
tipo: comando
tags: [sistema-multiagente]
description: Audita el proyecto contra buenas prácticas de ingeniería (repo, proceso, legibilidad del código) y devuelve los huecos priorizados con evidencia. No cambia nada.
argument-hint: [repo | codigo | proceso | todo] [api-core | web-app | ...]
---

# /practicas

Las otras revisiones miran **un cambio**: `/code-review`
la corrección de un diff, `security-review` su seguridad, el agente `adversary` cómo se rompe
en producción. Esta mira **el proyecto y la forma de trabajar**: lo que no aparece en ningún
diff porque falta en todos.

Compara contra dos referencias públicas, no contra mi opinión:
- [Microsoft Code-With Engineering Playbook](https://microsoft.github.io/code-with-engineering-playbook/)
  — ciclo completo: ramas, PRs, code review, testing, CI/CD, observabilidad, documentación.
- [Google Engineering Practices](https://google.github.io/eng-practices/) — code review y
  tamaño de los cambios (archivado en nov-2025, el contenido sigue vigente).

Y contra lo que ya decidió este proyecto: `docs/guias/PLAYBOOK-ANTI-REGRESIONES-Y-LECCIONES-APRENDIDAS.md`,
`docs/guias/PRINCIPIOS-INGENIERIA-MINIMALISTA.md` y `CLAUDE.md`. **Si una práctica del libro
contradice una decisión consciente del responsable, gana el responsable** — pero se dice que se está
desviando y por qué importa (ej. `UseHttpsRedirection` incondicional en 4 repos: deuda
aceptada, no hallazgo nuevo).

## Modos

`repo` · `codigo` · `proceso` · `todo` (por defecto). Segundo argumento opcional: qué repo.
Sin él, los 6.

### `repo` — el repositorio en GitHub
Con `gh`, sin tocar nada:
- Protección de `develop` y `main`: ¿se puede mergear sin revisión? ¿sin CI en verde?
- `CODEOWNERS`: ¿Revisor Principal queda como revisor automático o hay que acordarse de agregarlo?
- Permisos del `GITHUB_TOKEN` en los workflows (`permissions:` explícito y mínimo).
- Disparadores de CI: el `types: [opened]` de web-app hace que **el CI no corra al subir
  commits nuevos a un PR abierto** — verificado el 2026-09-21.
- Escaneo de secretos y bloqueo al hacer push; Dependabot.
- Ramas remotas sin mergear y sin actividad; PRs abiertos contra `main` por error.
- `.gitignore`: `appsettings.Development.json`, `.env`, artefactos generados.

### `codigo` — legibilidad y capacidad de revisión
El objetivo es **ver mejor el código**, no reescribirlo. Mide y lista, con `archivo:línea`:
- **Archivos gigantes** (>400 líneas) y **funciones largas** (>50): son donde se esconden los
  bugs y lo que hace impasable un PR.
- **Duplicación** de la misma regla en dos capas (el síntoma "Smart UI" del playbook §24).
- **Nombres que mienten**: una función que hace más de lo que dice, un `helper` cajón de
  sastre.
- **Comentarios que explican el qué** en vez del porqué; y lo contrario: decisiones raras sin
  una línea que las justifique.
- **Código sin test** en la lógica que importa (estado, dinero, concurrencia), y tests que no
  fallarían si rompes la regla que dicen cubrir.
- **Números y GUID sueltos** en el código en vez de catálogo o constante con nombre
  (el patrón vigente: códigos de catálogo como `TipoServicioCodigos`, no GUID que cambian entre entornos).

### `proceso` — cómo se llega de la idea al deploy
- **Tamaño de los PRs**: Google recomienda cambios chicos; mide líneas por PR de los últimos
  10 y nombra los que pasaron de 400.
- Tiempo desde que un PR se abre hasta que se revisa.
- Commits: convención, mensajes que expliquen el porqué.
- **Despliegue**: qué pasa con las migraciones (hoy **ninguna API migra sola**, y eso tuvo el
  dev caído 5 días en septiembre).
- Observabilidad: ¿hay logs útiles cuando algo falla en dev?
- Documentación viva: ¿las guías coinciden con el código, o quedaron atrás?

## Puntaje por área

Se puntúan **6 ejes**, no tres: con tres, el gráfico de araña es un triángulo y no dice nada.
Los ejes son los que de verdad se mueven por separado:

1. **Protección del repo** — ramas protegidas, revisión obligatoria, CODEOWNERS, secretos.
2. **CI/CD** — disparadores correctos, permisos mínimos, despliegue y migraciones.
3. **Revisión de código** — tamaño de los PRs, tiempo hasta la revisión, segundo par de ojos.
4. **Tests** — cobertura de lo que importa, y que fallen de verdad cuando algo se rompe.
5. **Legibilidad** — archivos y funciones manejables, nombres honestos, sin duplicación.
6. **Observabilidad** — logs útiles cuando algo falla, y guías que coinciden con el código.

Cada eje se puntúa de **0 a 10**, con criterio explícito para que el número no sea una
opinión y se pueda comparar mes a mes:

- Se parte de 10 y se descuenta por hallazgo: **−3 grave** (rompe producción, pierde datos o
  deja pasar código sin revisar), **−1,5 medio** (cuesta tiempo o esconde errores), **−0,5
  menor** (fricción).
- Piso en 0, y el número se redondea a un decimal.
- La nota global es el promedio de los 6 ejes, sin ponderar: el proyecto se cae por cualquiera.
- **Cada punto descontado se justifica con su hallazgo.** Un puntaje sin la lista que lo
  explica no se entrega.

Rangos: **8-10** sano · **6-8** con deuda manejable · **4-6** duele todas las semanas ·
**menos de 4** apaga incendios en vez de construir.

## Qué devolver

1. **Una tabla**, lo más grave primero:

   | Práctica | Qué dice | Qué hay hoy | Hueco | Prioridad |

2. **Las 3 a 5 acciones concretas** que más mueven la aguja, cada una con el comando o el
   archivo exacto. Nada de "mejorar la calidad": eso no se puede hacer el lunes.

3. **Un Artifact con el informe**, publicado y con su enlace. Misma estética de lámina que el
   tablero de avance (`.claude/tools/trello/plantilla_avance.py` es la referencia): papel
   blanco, líneas finas, sin tarjetas con sombra, tipografía con carácter para títulos y
   monoespaciada para las cifras, y contraste suficiente en el texto chico.

   Arriba, la **nota global** en grande con su rango en palabras.

   Debajo, un **gráfico de araña** con los 6 ejes, en **SVG escrito a mano, sin librerías**:
   - hexágono de referencia con anillos en 2, 4, 6, 8 y 10, en línea fina;
   - el polígono del puntaje relleno con el acento al 15% de opacidad y borde de 2px, con un
     punto de 8px en cada vértice;
   - **el nombre del eje y su puntaje en cada punta** (`Tests 6,5`), con el texto tomando el
     color de los tokens del tema para que se lea en claro y en oscuro;
   - `viewBox` con margen suficiente para que ninguna etiqueta se corte, y `fill` explícito en
     cada forma;
   - si hay auditoría anterior, su polígono en gris punteado detrás, para ver el movimiento.

   Al lado o debajo, **las mismas 6 cifras como filas con barra fina**: el araña se ve lindo
   pero se lee mal, y la barra es la que permite comparar. Después, los hallazgos agrupados
   por eje, cada uno con su evidencia (`archivo:línea` o comando) y los puntos que descontó.
   Al pie, las acciones concretas.

   **Cada corrida es un Artifact nuevo**, con la fecha en el título (`Prácticas · 21/09`), no
   una republicación del anterior: la gracia es poder comparar contra la auditoría pasada.

## Reglas

- **Evidencia o no se reporta.** Cada fila lleva `archivo:línea`, salida de comando o link al
  PR. Nada de "parece que…".
- **No cambia nada.** Ni código, ni configuración del repo, ni Trello. Solo propone, igual que
  el agente `system-auditor`.
- **No repitas lo que ya está decidido.** Antes de reportar, revisa el playbook y `CLAUDE.md`:
  varias cosas que parecen huecos son deuda aceptada y anotada.
- **Cinco hallazgos buenos valen más que treinta.** Si la lista pasa de diez, ordénala y corta.
- Lo que amerite trabajo va a [`/proyecto extra`](proyecto.md) con sus horas, para que entre en
  el tablero en vez de quedar en un informe que nadie retoma.

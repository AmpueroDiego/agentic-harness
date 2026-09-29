<!--
Plantilla de perfil de stack. Copia este archivo como <tu-stack>.md,
completa cada sección con información real y verificable (comandos que
de verdad corren, rutas que de verdad existen) y referencialo desde
harness.ini con stack_profile = <tu-stack>.
-->

## Stack real (verificado, no asumas otro)

<!-- Lenguaje, framework, versión, gestor de paquetes, librerías clave -->
<Lenguaje> · <Framework> · <versión> · <gestor de paquetes>

Comandos: `<build>` · `<test>` · `<lint>` · `<dev/run local>`.

Estructura por capas: <describe las carpetas reales del repo y qué va en
cada una>. Respeta la capa donde vive cada cosa; no mezcles responsabilidades
entre capas.

## HARD RULES — cada una viene de un bug real, no son preferencias de estilo

<!--
Cada regla de esta lista debería poder responder: "¿qué bug real evita?".
Si no lo sabes todavía, no la agregues acá — ponla en el plan de la tarea
que la originó y súbela acá recién cuando se repita una segunda vez.
-->

1. **<Regla 1>.** <qué bug evita, con archivo:línea del caso real si existe>
2. **<Regla 2>.** ...

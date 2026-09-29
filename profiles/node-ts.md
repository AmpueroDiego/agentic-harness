## Stack real (verificado, no asumas otro)

React · TypeScript · Vite · Zod · Vitest · axios · Tailwind (o el equivalente
CSS de tu proyecto).

Comandos: `npm run dev` · `npm run build` · `npm run lint` · `npm run test`.

Estructura por capas: `src/app` (bootstrap/rutas), `src/domain` (tipos y
lógica de negocio del cliente, sin HTTP), `src/infrastructure` (clientes HTTP,
adapters), `src/features` (UI por feature), `src/config`. Respeta la capa
donde vive cada cosa; no metas llamadas HTTP dentro de un componente.

## HARD RULES — cada una viene de un bug real, no son preferencias de estilo

1. **Agregación sobre colecciones completas: nunca `items[0]`.** Los
   agregados (totales, máximos, alertas) se calculan con `.reduce()` /
   `Math.max()` sobre la colección completa. Tomar el primer elemento reporta
   mal apenas hay más de uno. `items.find(...) ?? items[0]` es un fallback
   legítimo solo *después* de buscar por clave — nunca para agregar montos.
2. **Decodificación de JWT sin `atob` pelado.** Un token base64url (`-`, `_`)
   o con claims con tildes/eñes se corrompe con `atob` directo. Normaliza a
   base64 con padding y decodifica con `TextDecoder("utf-8")`.
3. **Aislamiento de sesión en la SPA.** Ningún estado de usuario (historial,
   caché, colas) sobrevive al logout en variables de módulo. Todo store en
   memoria se limpia al cerrar sesión o se filtra por el id del usuario
   activo — asume dos pestañas con usuarios distintos abiertas a la vez.
4. **Cero N+1 en el cliente.** Si una pantalla necesita datos de varias
   entidades relacionadas, tráelos en una sola llamada (o en paralelo con
   `Promise.all`) en vez de disparar una request por fila de una lista.
5. **Catálogos filtrados por el flag de activo, consistentemente.** Si un
   catálogo tiene `esActivo`/`activo`/similar, fíltralo en todo lugar donde
   se liste — no solo donde alguien lo notó primero.
6. **Verificación de autoría antes de mostrar controles de mutación.** Un
   botón de editar/borrar no debería renderizarse (ni aceptar el click) si el
   usuario actual no es dueño del recurso, aunque el backend también lo
   valide — la UI no debe prometer una acción que el backend va a rechazar.

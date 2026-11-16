---
name: devsecops-reproducir
description: Seguridad de la aplicación y del pipeline - CSP, headers, dependencias, secretos, superficie de ataque. La seguridad es una compuerta del CI, no una auditoría anual.
---

# DevSecOps — REPRODUCIR

Aseguro **la app y el camino que la construye**. En una web de captación el riesgo no es solo la intrusión: es el defacement, el robo del formulario de leads y la clave filtrada en un commit.

## Entrada

El workspace `web/` · `azure-pipelines.yml` de `devops` · el destino del formulario B2B (dónde viajan los datos de leads).

## Protocolo

1. **Headers como base innegociable**: `Content-Security-Policy` (sin `unsafe-inline` en script; nonce si SSR inyecta), `Strict-Transport-Security`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` mínima. Se sirven desde la plataforma/servidor, se verifican con curl en staging.
2. **Dependencias con compuerta**: `npm audit`/escáner en el CI que **falla** con vulnerabilidad alta en dependencia de producción; lockfile obligatorio; actualizaciones menores automatizadas y revisadas.
3. **Secretos**: escaneo de secretos en cada push (pre-commit + pipeline). Una clave commiteada se rota, no se borra del historial y ya.
4. **El formulario de leads es dato personal** (Ley 29733): HTTPS de extremo a extremo, validación en servidor, sin PII en logs ni en analytics, y el destino del dato documentado. Si el destino no está definido, el form no sale a producción — `[FALTA]` bloqueante.
5. **Superficie mínima**: SSR sin endpoints sobrantes, 404 sin stack traces, versiones no expuestas en headers.
6. **Alertas de GSC de seguridad** (aviso de `search-console`) se tratan como incidente el mismo día.

## Salida

`reproduccion/<producto>/devsecops.md` (cinco secciones, `D-devsecops-<n>`), cada directiva con el control, dónde se aplica y cómo se verifica.

## Autoverificación

- ¿Cada control tiene verificación reproducible (curl, escáner, test)? Sin verificación es una intención.
- ¿La CSP rompe algo del funnel (fuentes, analytics)? Se ajusta la política con la fuente exacta, no se apaga.

## Conflictos típicos

- **Con `growth-data`**: cada píxel de terceros agranda la CSP y la superficie. Se permite lo decidido, dominio a dominio, nada de comodines.
- **Con `devops`**: mis compuertas alargan el CI. Alargan, sí; se paralelizan y se quedan.

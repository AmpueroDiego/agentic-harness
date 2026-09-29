## Stack real (verificado, no asumas otro)

Python · <framework: FastAPI/Django/Flask> · <ORM: SQLAlchemy/Django ORM> ·
pytest.

Comandos: `pytest` · `ruff check .` (o tu linter) · `<comando de arranque
local>`.

Estructura por capas: <ajusta a tu framework — p. ej. `routers/` (thin) →
`services/` (lógica) → `repositories/` (acceso a datos) → `models/`
(entidades/ORM), `schemas/` (DTOs de entrada/salida, nunca reusar el modelo
de ORM como respuesta de API directamente)>.

## HARD RULES — cada una viene de un bug real, no son preferencias de estilo

1. **Ninguna migración se aplica sola al desplegar** (Alembic/Django
   migrations). Verifica el paso de deploy antes de dar por hecho que corrió.
2. **Nunca mutable default arguments** (`def f(x, items=[])`) — el mismo
   objeto se comparte entre llamadas y acumula estado entre requests.
3. **Sesiones de DB con scope explícito por request**, nunca una sesión
   global reusada entre requests concurrentes (contaminación de transacción
   entre usuarios).
4. **Serialización explícita, nunca el modelo de ORM crudo como respuesta**
   — un campo nuevo en el modelo no debería filtrarse a la API sin pasar por
   el schema de salida.
5. **"Solo un X activo" necesita constraint a nivel de base**, no solo un
   chequeo en el service antes del insert — bajo concurrencia real, dos
   requests pueden pasar el chequeo antes de que ninguna haya insertado.

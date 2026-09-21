---
name: security
description: >-
  Catálogo de seguridad transversal para AcmeOrg: mapeo de CWEs, OWASP Top 10,
  mitigaciones arquitectónicas en .NET/React y gestión de alertas de dependencias (GitHub/NuGet/npm).
---

# 🛡️ Guía de Seguridad, CWE, OWASP y Alertas de Dependencias (AcmeOrg)

Este skill provee las directrices de seguridad, el inventario de **CWE (Common Weakness Enumeration)**, alineación con **OWASP Top 10** y las políticas de mitigación de vulnerabilidades en librerías (NuGet / npm / GitHub Dependabot) para el ecosistema AcmeOrg (`api-core`, `web-app`, `api-contracts`, `api-people`, `api-auth`, `api-delivery`).

---

## 📑 1. Catálogo CWE y Mapeo OWASP Top 10

| CWE ID | Vulnerabilidad / Debilidad | OWASP Top 10 | Contexto en AcmeOrg | Mitigación Implementada |
| :--- | :--- | :--- | :--- | :--- |
| **CWE-502** | *Deserialization of Untrusted Data* | **A08:2021** Software and Data Integrity Failures | Deserialización de payloads en tablas de Outbox / colas de background. | Uso de `System.Text.Json` con `OutboxEventTypeRegistry` (lista blanca estricta `Type -> System.Type`). Prohibido `Newtonsoft.Json` con `TypeNameHandling.All`. |
| **CWE-190** | *Integer Overflow or Wraparound* | **A04:2021** Insecure Design | Cálculo exponencial $2^n \times \text{delay}$ en políticas de reintento de Quartz. | Cálculo intermedio en `double` con acotación estricta (`Math.Clamp`) contra `MaxDelaySeconds`. |
| **CWE-362** | *Concurrent Execution using Shared Resource (Race Condition)* | **A04:2021** Insecure Design | Desactivación manual de mensajes mientras el Job procesa la fila; asignación concurrente de casos. | `UPDATE` atómico condicional (`WHERE Status <> 'Processing'`) e índice único `IX_CasoAsignacion_CasoId_Activa`. |
| **CWE-798** / **CWE-200** | *Use of Hard-coded Credentials / Information Exposure* | **A02:2021** Cryptographic Failures | Cadenas de conexión a Azure SQL / Redis / credenciales de APIs en Git. | Política de Cero Secretos en `appsettings.json`, Service Discovery vía `IApiAuthService`, User Secrets en local y Key Vault en Azure. |
| **CWE-862** | *Missing Authorization* | **A01:2021** Broken Access Control | Controladores expuestos sin validación de JWT o roles no restringidos. | Directiva `[Authorize]` en `BaseApiController`, roles explícitos en endpoints de negocio y pruebas de arquitectura automáticas (`ControllerAuthorizationTests`). |
| **CWE-942** | *Permissive Cross-Origin Resource Sharing (CORS)* | **A05:2021** Security Misconfiguration | Orígenes no restringidos en entornos de producción. | CORS permisivo habilitado **únicamente en `Environment.IsDevelopment()`** para desarrollo local (macOS/Vite); orígenes estrictos validados en producción. |
| **CWE-345** | *Insufficient Verification of Data Authenticity* | **A07:2021** Identification and Authentication Failures | Manejo de tokens JWT en .NET 10 (`JsonWebToken` vs `JwtSecurityToken`). | `SignatureValidator` tolerante a ambos tipos de token en middleware de autenticación sin delegar validación insegura. |
| **CWE-400** | *Uncontrolled Resource Consumption (DoS)* | **A04:2021** Insecure Design | Reintentos infinitos ante fallos definitivos de pasarelas externas. | Clasificación de excepciones con `IsTransientException`: errores 4xx van a `DeadLetter` de inmediato sin reintento; zombi-recovery acotado con clamp $\ge 1$ min. |

---

## 📦 2. Monitoreo y Alertas de Librerías (GitHub Dependabot / NuGet / npm)

### 🔹 Librerías Backend (.NET / NuGet)

1. **`Newtonsoft.Json` (CVE-2024-38063 / DoS & Type Handling):**
   * *Regla:* Priorizar `System.Text.Json` para todas las nuevas características y serialización de dominio.
   * *Si se requiere `Newtonsoft`:* Fijar versión $\ge 13.0.3$ y NUNCA activar `TypeNameHandling.All` ni `TypeNameHandling.Auto`.

2. **`Microsoft.Data.SqlClient` (Vulnerabilidades TLS / Connection Hijacking):**
   * *Regla:* Mantener versión $\ge 5.1.5$ o $\ge 5.2.0$.
   * *Configuración:* Asegurar `Encrypt=True;TrustServerCertificate=False` en entornos productivos de Azure.

3. **`Dapper` (Inyección SQL por concatenación de parámetros):**
   * *Regla:* Usar versión $\ge 2.1.35$ / `2.1.66`.
   * *Buenas prácticas:* Siempre pasar parámetros vía objetos anónimos o `DynamicParameters` (PROHIBIDO interpolar strings directamente en consultas Dapper).

4. **`Quartz.NET` (Threadpool Starvation & Deserialización JobDataMap):**
   * *Regla:* Mantener versión $\ge 3.13.0$ / `3.15.0`.
   * *Buenas prácticas:* Usar decorador `[DisallowConcurrentExecution]` para evitar solapamiento de workers y no almacenar objetos complejos serializados en `JobDataMap`.

---

### 🔹 Librerías Frontend (React / Vite / npm)

1. **`Axios` / `Fetch Wrappers` (SSRF / Prototype Pollution):**
   * *Regla:* Sanitizar parámetros de URL y headers de autorización. No exponer tokens JWT en `localStorage` si es posible manejarlos en cookies `HttpOnly` o memoria de sesión.

2. **`@tanstack/react-query` (Stale Cache & Memory Leaks):**
   * *Regla:* Configurar `staleTime` y `gcTime` explícitos en mutaciones de datos sensibles para evitar lecturas de caché desactualizadas por otros operadores.

---

## 🛠️ 3. Checklist de Auditoría de Seguridad para Agentes

Antes de cerrar cualquier desarrollo o PR en AcmeOrg, verificar:

- [ ] **Secretos:** ¿`appsettings.json` tiene cadenas vacías o `"REPLACE_ME"` (0 contraseñas o connection strings reales)?
- [ ] **M2M Auth:** ¿El servicio utiliza su propia identidad registrada en `api-auth`?
- [ ] **CORS / SSL:** ¿`app.UseHttpsRedirection()` está condicionado a `!app.Environment.IsDevelopment()`?
- [ ] **SQL Injection:** ¿Todas las consultas Dapper / EF Core utilizan parámetros (`@Param` o `$"""...{param}"""`) sin concatenar strings?
- [ ] **Concurrencia:** ¿Las operaciones críticas tienen control de locks (`ROWLOCK, UPDLOCK`) o `WHERE` condicionales?
- [ ] **Validación de Dependencias:** ¿Las versiones de paquetes NuGet y npm cumplen las versiones mínimas seguras?

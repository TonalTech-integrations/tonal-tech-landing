# 002 - Sistema de leads y cotizaciones B2B (fase manual, diseño listo para IA)

- **Estado:** aprobada (2026-10-01)
- **Fecha:** 2026-09-24
- **Autor:** Equipo Tonal-Tech

## 1. Resumen

Las 4 secciones cotizables de la landing (Optimización Comercial y Analítica, Arquitectura e Infraestructura Cloud, Ciberseguridad Avanzada y Cumplimiento, Soporte de Cómputo e Infraestructura Física) hoy solo abren un panel de leads **simulado** (`components/lead-panel.tsx`): el envío se resuelve con `setTimeout(2600ms)` y no hay backend, persistencia, estados, agente humano ni cotización.

Esta spec reemplaza esa simulación por un **sistema real de leads y cotizaciones B2B en fase manual**: el lead se persiste, pasa por estados (`recibido → en_revision → cotizado → cerrado`), puede asignarse a un agente humano y un administrador genera la cotización. El diseño separa la **generación de cotización detrás de una interfaz de servicio** (`QuoteService`) de modo que en la Fase 4 del roadmap (spec 001) se pueda insertar una implementación por IA sin tocar el resto del sistema.

## 2. Objetivos

- Persistir leads reales de las 4 secciones cotizables con validación de servidor.
- Implementar el flujo de estados y la asignación a agente humano.
- Permitir que un administrador genere y almacene cotizaciones por lead (fase manual).
- Reemplazar el `setTimeout` del `LeadProvider` por una llamada HTTP real a `POST /leads`.
- Dejar el diseño desacoplado (`QuoteService`) para migrar a cotización por IA en Fase 4 sin cambios estructurales.
- Proveer los endpoints que el dashboard admin (spec 005) consumirá para gestionar leads.

## 3. Alcance

### Incluye
- Modelo de datos: `Lead`, `Quote`, `QuoteParams` (parámetros de cotización por servicio).
- Endpoints públicos y de administración (listados en 5.2).
- Integración del `LeadProvider` existente con el backend (reemplazo del `setTimeout`).
- Validación de email en servidor (resuelve el riesgo #11 de ANALISIS-PROYECTO.md).
- Interfaz `QuoteService` con implementación `ManualQuoteService` (la IA queda como `AIQuoteService` futuro).
- Especificación SDD + casos TDD Vanilla.

### Excluye
- Implementación de la IA de cotización (Fase 4; solo se define la interfaz).
- UI del panel de gestión de leads (la construye la spec 005; aquí solo se definen los endpoints).
- Notificaciones por email al cliente o al agente (se puede añadir en iteración posterior).
- Integración con CRM externo.

## 4. Requisitos

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| R1 | `POST /leads` público que valide email en servidor y persista el lead con estado inicial `recibido` | Alta |
| R2 | El lead debe registrar la sección de origen (6 categorías: 4 cotizables + `labs`/`academy` como consulta general) | Alta |
| R3 | `GET /admin/leads` con filtros (estado, categoría, rango de fechas) y orden por fecha descendente | Alta |
| R4 | `GET /admin/leads/{id}` con detalle del lead, su cotización y parámetros | Alta |
| R5 | `PATCH /admin/leads/{id}` para cambiar estado y asignar agente humano | Alta |
| R6 | `POST /admin/leads/{id}/quote` para crear la cotización manual (monto, moneda, vigencia, notas) | Alta |
| R7 | `GET /admin/leads/{id}/quote` para consultar la cotización del lead | Media |
| R8 | Transición de estados validada: `recibido → en_revision → cotizado → cerrado` (sin saltos inválidos) | Alta |
| R9 | `LeadProvider` reemplaza `setTimeout` por llamada real a `POST /leads` con estados de UI (enviando / éxito / error) | Alta |
| R10 | Interfaz `QuoteService` desacoplada (`generate(lead, params) -> Quote`) con implementación manual | Media |
| R11 | Los endpoints `/admin/leads*` exigen JWT + `is_admin` (mismo patrón que `backend/routers/admin.py`) | Alta |
| R12 | Los parámetros de cotización por servicio (`QuoteParams`) se almacenan como JSON versionado | Media |

## 5. Diseño / Arquitectura

### 5.1 Modelo de datos (backend/services/persistence.py)

**Tabla `leads`**

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | |
| `service_category` | str | Enum: `optimizacion-comercial`, `arquitectura-cloud`, `ciberseguridad`, `soporte-computo` (cotizables) + `labs`, `academy` (consulta general) |
| `contact_name` | str | Nombre del contacto (`form.name` del panel) |
| `email` | str | Validado con `EmailStr` en servidor; normalizado a minúsculas |
| `company_size` | str | Uno de `companySizes` del formulario (`Mediana empresa`, `Grande / Enterprise`, `Profesional independiente`) |
| `message` | text | Necesidades del cliente (`form.requirements` del panel) |
| `status` | str | Enum: `recibido`, `en_revision`, `cotizado`, `cerrado`; default `recibido` |
| `assigned_agent_id` | int FK users.id | Nullable; agente humano asignado |
| `created_at` | datetime | |
| `updated_at` | datetime | Se actualiza en cada cambio de estado/asignación |

**Tabla `quotes`**

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | |
| `lead_id` | int FK leads.id | Único (1 cotización activa por lead; se puede versionar) |
| `amount_cents` | int | Monto en centavos; `>= 0` (0 permitido, negativo → 422) |
| `currency` | str | Default `mxn` |
| `valid_until` | date | Vigencia de la cotización |
| `notes` | text | Notas del agente |
| `created_by` | int FK users.id | Admin que la generó |
| `created_at` | datetime | |

**Tabla `quote_params`**

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | |
| `lead_id` | int FK leads.id | |
| `service_category` | str | Misma categoría del lead |
| `params` | JSON | Respuestas/parámetros recolectados (hoy: mensaje estructurado; en Fase 4: respuestas del diálogo de IA) |
| `version` | int | Versionado del esquema de parámetros |
| `created_at` | datetime | |

### 5.2 Endpoints REST

**Públicos (sin autenticación):**

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/leads` | Crea un lead. Body: `{service_category, contact_name, email, company_size, message}` (exactamente lo que recolecta el formulario actual). Respuesta 201 con el lead creado (sin datos sensibles de más). Errores: 422 (validación, email inválido, company_size fuera de lista), 400 (categoría desconocida) |

**Administración (JWT + `is_admin`, vía `require_admin` de `backend/routers/admin.py`):**

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/admin/leads` | Lista leads. Query: `status?`, `service_category?`, `from?`, `to?`, `page?`, `page_size?` (default 20). Orden: `created_at` desc |
| GET | `/admin/leads/{lead_id}` | Detalle: lead + quote + quote_params |
| PATCH | `/admin/leads/{lead_id}` | Body: `{status?, assigned_agent_id?}`. Valida transición de estados y que el agente exista |
| POST | `/admin/leads/{lead_id}/quote` | Crea/actualiza cotización. Body: `{amount_cents, currency?, valid_until, notes?}`. Requiere lead en estado `en_revision` o `cotizado`; al crearla, el lead pasa a `cotizado` |
| GET | `/admin/leads/{lead_id}/quote` | Devuelve la cotización o 404 si no existe |

**Nota:** el router nuevo `backend/routers/leads.py` se registra en `backend/main.py` con prefijo `/leads` y `/admin/leads` (o un solo router con ambos grupos). Los endpoints de administración reutilizan `require_admin` para no duplicar lógica.

### 5.3 Interfaz de servicio de cotización (desacoplada para IA)

```python
# backend/services/quote_service.py
class QuoteService(Protocol):
    def generate(self, lead: Lead, params: QuoteParams) -> Quote: ...

class ManualQuoteService:
    """Fase manual: el agente humano define monto/vigencia vía POST /admin/leads/{id}/quote."""
    def generate(self, lead, params) -> Quote: ...

# Fase 4 (futuro): class AIQuoteService(QuoteService) — misma interfaz.
# La IA recolecta lo necesario por sección, genera la cotización con
# parámetros de BD y deriva a agente humano si se requiere.
```

- El endpoint `POST /admin/leads/{id}/quote` delega en `ManualQuoteService` (hoy).
- En Fase 4 se intercambia la implementación por `AIQuoteService` sin cambiar endpoints ni modelo.
- `QuoteParams` es el contrato de entrada: hoy se llena con el mensaje estructurado del lead; en Fase 4 con las respuestas del diálogo de IA.
- **Decisión (aprobada 2026-10-01):** la fila `quote_params` se crea automáticamente al crear el lead (`POST /leads`), con `version=1` y `params` = mensaje estructurado del formulario (`{"source": "lead_panel", "message", "company_size"}`). La IA de 008 la regenerará con las respuestas del diálogo.
- **Corrección (2026-10-01, 002-03):** la sub-spec 002-03 asumía "sin cotización → `quote: null` **y `quote_params: null`**", pero por la decisión anterior todo lead nace con `quote_params` v1. Corregido: sin cotización → `quote: null` y `quote_params` presente; solo un lead sin fila `quote_params` (legado, pre-decisión) devuelve ambos `null`.

### 5.4 Integración con el LeadProvider existente (components/lead-panel.tsx)

- Reemplazar `window.setTimeout(() => setStage('done'), 2600)` por una llamada a `POST /leads` vía `lib/api.ts` (nueva función `createLead(payload)`).
- Estados de UI: se **reutiliza el stage existente `diagnosing`** (con su `DiagnosticTicker`) como estado de envío; se **agrega un nuevo stage `error`**. Flujo: `form → diagnosing → done | error`.
- El `presetService` que hoy recibe `openLead(service.title)` se mapea al `service_category` del backend. **Bug preexistente a corregir:** los títulos de `services[]` no coinciden con `serviceCategoriesForm` (p. ej. `"Ciberseguridad Avanzada y Cumplimiento"` vs `"Ciberseguridad Avanzada"`), así que el pill preseleccionado no se activa. La implementación mapea por `id` estable del servicio (`optimizacion`/`cloud`/`ciberseguridad`/`soporte` → `optimizacion-comercial`/`arquitectura-cloud`/`ciberseguridad`/`soporte-computo`) y no por título.
- Payload enviado: `{service_category, contact_name: form.name, email: form.email, company_size: form.size, message: form.requirements}`.
- Validación de email: se mantiene la regex del cliente como UX inmediata, pero la validación **autoritativa** pasa al servidor (`EmailStr` de Pydantic → 422).
- `lib/api.ts` ya maneja JWT en localStorage; `POST /leads` no requiere token. **Ajuste necesario:** `apiFetch` debe normalizar el `detail` de Pydantic (lista de objetos en 422) a un mensaje legible, porque hoy asume que `detail` es un string.

### 5.5 Flujo de estados

```
recibido ──► en_revision ──► cotizado ──► cerrado
   │             │              │
   └─────────────┴──────────────┘ (cerrado puede alcanzarse desde cualquier estado:
                                    lead descartado, cliente no interesado, etc.)
```

- Transiciones válidas: `recibido → en_revision`, `recibido → cerrado`, `en_revision → cotizado`, `en_revision → cerrado`, `cotizado → cerrado`.
- Transiciones inválidas (ej. `recibido → cotizado` sin pasar por `en_revision`, o `cotizado → en_revision`): 400 con detalle.
- `cerrado` es estado terminal: toda transición desde `cerrado` es 400.
- `POST /admin/leads/{id}/quote` solo se permite en `en_revision` o `cotizado` (re-cotización); al crear la cotización el estado pasa a `cotizado`.

## 6. Criterios de aceptación

- [x] `POST /leads` persiste un lead con estado `recibido` y rechaza email inválido con 422 (002-01, 2026-10-01).
- [x] Un lead creado desde la landing aparece en `GET /admin/leads` sin reiniciar el backend (002-02, 2026-10-01).
- [x] `GET /admin/leads/{id}` devuelve `{lead, quote, quote_params}`; 404 si el lead no existe; `quote` `null` sin cotización y `quote_params` presente (002-03, 2026-10-01).
- [ ] `PATCH /admin/leads/{id}` cambia estado y asigna agente; las transiciones inválidas devuelven 400.
- [ ] `POST /admin/leads/{id}/quote` crea la cotización y mueve el lead a `cotizado`.
- [ ] Los endpoints `/admin/leads*` devuelven 401 sin token (FastAPI `HTTPBearer` responde 401 sin credenciales (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima)) y 403 para usuario no admin.
- [ ] El `LeadProvider` muestra `diagnosing` durante la llamada real y `done`/`error` según el resultado; ya no usa `setTimeout`.
- [ ] Existe `QuoteService` como interfaz y `ManualQuoteService` como implementación; el endpoint de cotización depende de la interfaz, no de la implementación.
- [ ] `QuoteParams` almacena los parámetros por servicio como JSON versionado.

## 7. Riesgos y consideraciones

- **Spam/abuso en `POST /leads`:** endpoint público. Considerar limitación de tasa por IP (p. ej., middleware simple o campo honeypot) en iteración posterior; mínimo, validación estricta de email y longitud de campos.
- **Datos personales:** el lead contiene PII (email, nombre, tamaño de empresa). Documentar retención y no exponerla en respuestas públicas.
- **Fase 4 (IA):** la calidad de la cotización por IA depende de parámetros de BD por servicio; `QuoteParams` debe versionarse para no romper cotizaciones históricas.
- **Dependencia con 005:** la UI de gestión de leads se construye en la spec 005; esta spec solo define API y modelo. El dashboard no debe bloquearse si 005 se retrasa (se puede probar con curl/Postman).
- **`assigned_agent_id`:** validar que el usuario asignado exista y tenga rol de agente/admin; hoy el modelo solo tiene `is_admin`, por lo que la asignación se limita a admins (extensible a rol `agent` en el futuro).
- **Interacción con 003 (decisión 2026-10-01):** cuando se implemente la spec 003, la tarjeta Labs de `ServiceGrid` dejará de abrir el panel de leads (navegará a `/labs`); la categoría `labs` seguirá siendo seleccionable únicamente vía el pill `'Tonal-Tech Labs (Mobile)'` del formulario. El mapeo `labs → labs` de 002-08 se conserva para cualquier apertura programática del panel con ese id.
- **Tests frontend colocados (decisión 2026-10-01):** las suites de los sub-specs 002-07/08/09 se colocan junto al componente (`components/*.test.tsx`), patrón ya usado por los tests de Academy (007), en lugar de `__tests__/`. Las rutas de suite indicadas en los sub-specs son solo sugeridas.

## 8. Especificación funcional (SDD)

### 8.1 `POST /leads` (público)

- **Entrada:** `{service_category, contact_name, email, company_size, message}`.
- **Salida:** 201 `{id, service_category, contact_name, email, company_size, status: "recibido", created_at}`.
- **Reglas de negocio:**
  - `service_category` debe ser una de las 6 categorías; si no → 400. Las 4 cotizables alimentan la cotización (y la IA de 008); `labs` y `academy` entran al mismo pipeline como consulta general (la cotización es opcional para ellas).
  - `email` debe ser válido (`EmailStr`); si no → 422.
  - `company_size` debe ser uno de los 3 valores de `companySizes`; si no → 422.
  - `contact_name` obligatorio, mínimo 2 caracteres (alineado con la validación del formulario) → 422 si no cumple.
  - `message` obligatorio con longitud mínima 5 caracteres tras `trim` (alineado con la validación actual del formulario, `trim().length > 4`) → 422 si no cumple.
  - El lead se crea siempre con `status="recibido"` y `assigned_agent_id=None`.
- **Casos borde:** email con espacios/Mayúsculas (normalizar a minúsculas); `service_category` con acentos o etiquetas de UI (el frontend mapea por `id` de servicio antes de enviar; el backend nunca recibe etiquetas de UI); mensaje vacío; campos extra en el body (Pydantic los ignora).

### 8.2 `GET /admin/leads` (admin)

- **Entrada:** query `status?`, `service_category?`, `from?`, `to?`, `page?`, `page_size?`.
- **Salida:** `{items: [LeadSummary...], total, page, page_size}`.
- **Reglas:** solo admins; filtros combinables; `from`/`to` filtran por `created_at`; orden `created_at` desc; `page_size` máx. 100; `page_size > 100` → 422.
- **Casos borde:** filtros sin resultados (lista vacía, `total=0`); fechas inválidas → 422; `page` fuera de rango → lista vacía, no error.

### 8.3 `PATCH /admin/leads/{lead_id}` (admin)

- **Entrada:** `{status?, assigned_agent_id?}` (al menos uno).
- **Salida:** lead actualizado.
- **Reglas:** transiciones válidas según 5.5; si `assigned_agent_id` se envía, el usuario debe existir (404 si no); al cambiar estado se actualiza `updated_at`.
- **Casos borde:** transición inválida → 400 con detalle en el formato `"Transición inválida: {estado_actual} -> {estado_solicitado}. Permitidas desde {estado_actual}: {lista}"` (ej. `"Transición inválida: recibido -> cotizado. Permitidas desde recibido: en_revision, cerrado"`); transición desde `cerrado` → 400 (estado terminal); lead inexistente → 404; body vacío → 422; asignar agente inexistente → 404.

### 8.4 `POST /admin/leads/{lead_id}/quote` (admin)

- **Entrada:** `{amount_cents, currency?, valid_until, notes?}`.
- **Salida:** 201 cotización creada (o 200 si se actualiza la existente).
- **Reglas:** `amount_cents >= 0`; `valid_until` en el futuro; el lead debe estar en `en_revision` o `cotizado`; al crear/actualizar, el lead pasa a `cotizado`; delega en `QuoteService.generate`.
- **Casos borde:** lead en `recibido` → 400 ("El lead debe estar en revisión"); `amount_cents` negativo → 422; `valid_until` en el pasado → 422; cotización existente → se actualiza (no duplica).

### 8.5 `LeadProvider` (frontend)

- **Entrada:** `openLead(presetService?)` abre el panel; el formulario envía los datos.
- **Salida:** estados `form → diagnosing → done | error`.
- **Reglas:** al enviar, se llama `createLead` (POST /leads); en éxito → `done`; en error de red o 4xx → `error` con mensaje y botón de reintento; el panel no se cierra durante `diagnosing`; el preset se resuelve por `id` de servicio (nunca por título) a una categoría válida.
- **Casos borde:** backend caído (error de red) → mensaje claro, sin pérdida de datos del formulario; 422 de validación → mostrar el mensaje normalizado del servidor; doble clic en enviar → deshabilitar botón durante `diagnosing`.

## 9. Casos de prueba (TDD Vanilla)

- `test_create_lead_persists_with_status_recibido`: Arrange: payload válido con email correcto. Act: `POST /leads`. Assert: 201, `status == "recibido"`, `assigned_agent_id is None`, el registro existe en BD.
- `test_create_lead_rejects_invalid_email`: Arrange: payload con `email="no-es-email"`. Act: `POST /leads`. Assert: 422 (validación Pydantic).
- `test_create_lead_rejects_unknown_service_category`: Arrange: payload con `service_category="otra-cosa"`. Act: `POST /leads`. Assert: 400.
- `test_create_lead_accepts_labs_and_academy_categories`: Arrange: payload con `service_category="labs"` (y luego `"academy"`). Act: `POST /leads`. Assert: 201, lead persistido con estado `recibido` como consulta general.
- `test_create_lead_rejects_unknown_company_size`: Arrange: payload con `company_size="Micro empresa"`. Act: `POST /leads`. Assert: 422.
- `test_create_lead_rejects_message_too_short`: Arrange: payload con `message="hola"` (4 caracteres tras trim). Act: `POST /leads`. Assert: 422.
- `test_create_lead_normalizes_email_to_lowercase`: Arrange: payload con `email="Cliente@Empresa.com"`. Act: `POST /leads`. Assert: el email persistido es `cliente@empresa.com`.
- `test_list_leads_requires_admin`: Arrange: token de usuario normal. Act: `GET /admin/leads`. Assert: 403.
- `test_list_leads_requires_auth`: Arrange: sin token. Act: `GET /admin/leads`. Assert: 401 (FastAPI `HTTPBearer` responde 401 sin credenciales (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima)).
- `test_list_leads_filters_by_status_and_category`: Arrange: 3 leads (2 `recibido`, 1 `cotizado`; 1 de `ciberseguridad`). Act: `GET /admin/leads?status=recibido&service_category=ciberseguridad`. Assert: solo el lead que cumple ambos filtros.
- `test_list_leads_orders_by_created_at_desc`: Arrange: 2 leads con fechas distintas. Act: `GET /admin/leads`. Assert: el más reciente aparece primero.
- `test_list_leads_rejects_page_size_over_100`: Arrange: token admin. Act: `GET /admin/leads?page_size=101`. Assert: 422 (`page_size > 100` → 422).
- `test_patch_lead_changes_status_and_assigns_agent`: Arrange: lead `recibido`, agente admin existente. Act: `PATCH /admin/leads/{id}` con `{status:"en_revision", assigned_agent_id: X}`. Assert: 200, estado y agente actualizados.
- `test_patch_lead_rejects_invalid_transition`: Arrange: lead `recibido`. Act: `PATCH` con `{status:"cotizado"}` (salto inválido). Assert: 400 con detalle de transición permitida.
- `test_patch_lead_404_when_agent_not_found`: Arrange: lead existente. Act: `PATCH` con `assigned_agent_id=99999`. Assert: 404.
- `test_create_quote_moves_lead_to_cotizado`: Arrange: lead en `en_revision`. Act: `POST /admin/leads/{id}/quote` con monto y vigencia válidos. Assert: 201, cotización creada, lead en `cotizado`.
- `test_create_quote_rejected_when_lead_recibido`: Arrange: lead en `recibido`. Act: `POST /admin/leads/{id}/quote`. Assert: 400.
- `test_create_quote_rejects_negative_amount`: Arrange: lead en `en_revision`. Act: quote con `amount_cents=-1`. Assert: 422.
- `test_create_quote_accepts_zero_amount`: Arrange: lead en `en_revision`. Act: quote con `amount_cents=0`. Assert: 201 (0 es válido según `amount_cents >= 0`; solo el negativo es 422).
- `test_create_quote_updates_existing_quote_not_duplicates`: Arrange: lead con cotización existente. Act: `POST /admin/leads/{id}/quote` de nuevo. Assert: 200 y una sola fila en `quotes` para ese lead.
- `test_quote_service_interface_swappable`: Arrange: `ManualQuoteService` registrado. Act: invocar el endpoint de cotización. Assert: delega en la interfaz `QuoteService` (inyección por dependencia), permitiendo reemplazar por `AIQuoteService` sin cambios de endpoint.
- `test_lead_provider_calls_real_endpoint_not_set_timeout`: Arrange: mock de `createLead` resolviendo. Act: enviar el formulario del panel. Assert: `createLead` invocado con el payload mapeado (`service_category` derivado del `id` del servicio, `company_size` incluido) y la UI pasa por `diagnosing` → `done`; no existe `setTimeout` en el flujo de envío.
- `test_lead_provider_shows_error_and_keeps_form_on_failure`: Arrange: mock de `createLead` rechazando. Act: enviar. Assert: estado `error`, mensaje visible, datos del formulario intactos, botón de reintento presente.
- `test_lead_provider_disables_submit_while_sending`: Arrange: mock de `createLead` con promesa pendiente. Act: enviar y hacer doble clic. Assert: el botón está deshabilitado y `createLead` se invoca una sola vez.
- `test_preset_service_maps_by_service_id_not_title`: Arrange: panel abierto vía `openLead` desde la tarjeta de Ciberseguridad. Act: inspeccionar el pill seleccionado. Assert: el pill de `serviceCategoriesForm` correspondiente queda activo (regresión del bug: `"Ciberseguridad Avanzada y Cumplimiento"` ≠ `"Ciberseguridad Avanzada"`).
- `test_api_fetch_normalizes_pydantic_422_detail`: Arrange: mock de fetch respondiendo 422 con `detail` como lista de errores Pydantic. Act: llamar `createLead`. Assert: el `Error` lanzado trae un mensaje legible (no `[object Object]`).

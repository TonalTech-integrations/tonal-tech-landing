# 002-01 - Crear lead público (POST /leads)

- **Spec padre:** [002 - Sistema de leads y cotizaciones B2B](../../002-cotizacion-b2b.md) (secciones: 5.1, 5.2, 5.4, 8.1, 6, 7)
- **Estado:** implementada (2026-10-01)
- **Fecha:** 2026-09-28
- **Tipo:** Backend
- **Dependencias:** Ninguna
- **Suite de pruebas sugerida:** Sugerida: `backend/tests/test_leads_crear_lead_publico.py`

## 1. Descripción

Endpoint público `POST /leads` que persiste los leads de las 4 secciones cotizables de la landing (más `labs`/`academy` como consulta general) con validación de servidor: email (`EmailStr`), `company_size` y longitudes mínimas. Reemplaza la simulación actual del panel de leads y resuelve el riesgo #11 de ANALISIS-PROYECTO.md (validación de email en servidor). El lead se crea siempre con estado `recibido` y sin agente asignado.

## 2. Requisitos cubiertos

| ID padre | Requisito | Prioridad |
|----------|-----------|-----------|
| R1 | `POST /leads` público que valide email en servidor y persista el lead con estado inicial `recibido` | Alta |
| R2 | El lead debe registrar la sección de origen (6 categorías: 4 cotizables + `labs`/`academy` como consulta general) | Alta |

## 3. Diseño

**Modelo (5.1, backend/services/persistence.py, tabla `leads`):** campos `id`, `service_category` (enum: `optimizacion-comercial`, `arquitectura-cloud`, `ciberseguridad`, `soporte-computo` + `labs`, `academy`), `contact_name`, `email` (validado con `EmailStr`, normalizado a minúsculas), `company_size` (uno de `companySizes`), `message`, `status` (default `recibido`), `assigned_agent_id` (nullable), `created_at`, `updated_at`.

**Endpoint (5.2):** `POST /leads` — público, sin autenticación.
- Body: `{service_category, contact_name, email, company_size, message}` (exactamente lo que recolecta el formulario actual).
- Respuesta: 201 con el lead creado: `{id, service_category, contact_name, email, company_size, status, created_at}` (no se expone `message` ni `assigned_agent_id`).
- Errores: 422 (validación, email inválido, `company_size` fuera de lista), 400 (categoría desconocida).

**Mapeo id de servicio → `service_category` (5.4; detalle en 002-08):**

| id en `services[]` (`lib/tonal-data.ts`) | `service_category` (backend) |
|------------------------------------------|------------------------------|
| `optimizacion` | `optimizacion-comercial` |
| `cloud` | `arquitectura-cloud` |
| `ciberseguridad` | `ciberseguridad` |
| `soporte` | `soporte-computo` |
| `labs` | `labs` |
| `academy` | `academy` |

Nota: `labs` es un id real en `services[]` de `lib/tonal-data.ts` (tarjeta "Tonal-Tech Labs" del `ServiceGrid`); `academy` NO tiene tarjeta en `services[]`, solo el pill `'Formación / Academy'` de `serviceCategoriesForm`. El frontend mapea por `id` de servicio antes de enviar (nunca por título); ver 002-08.

**Payload del frontend (5.4):** `{service_category, contact_name: form.name, email: form.email, company_size: form.size, message: form.requirements}`.

## 4. Especificación funcional (SDD)

- **Entrada:** `{service_category, contact_name, email, company_size, message}`.
- **Salida:** 201 `{id, service_category, contact_name, email, company_size, status: "recibido", created_at}`. La respuesta incluye exactamente esos campos: NO se expone `message` ni `assigned_agent_id`.
- **Reglas de negocio:**
  - `service_category` debe ser una de las 6 categorías; si no → 400. Las 4 cotizables alimentan la cotización (y la IA de 008); `labs` y `academy` entran al mismo pipeline como consulta general (la cotización es opcional para ellas).
  - `email` debe ser válido (`EmailStr`); si no → 422.
  - `company_size` debe ser uno de los 3 valores de `companySizes`; si no → 422.
  - `contact_name` obligatorio, mínimo 2 caracteres (alineado con la validación del formulario) → 422 si no cumple.
  - `message` obligatorio con longitud mínima 5 caracteres tras `trim` (alineado con la validación actual del formulario, `trim().length > 4`) → 422 si no cumple.
  - El lead se crea siempre con `status="recibido"` y `assigned_agent_id=None`.
- **Casos borde:** email con espacios/Mayúsculas (normalizar a minúsculas); `service_category` con acentos o etiquetas de UI (el frontend mapea por `id` de servicio antes de enviar; el backend nunca recibe etiquetas de UI); mensaje vacío; campos extra en el body (Pydantic los ignora).

## 5. Criterios de aceptación

- [x] `POST /leads` persiste un lead con estado `recibido` y rechaza email inválido con 422.
- [x] `POST /leads` rechaza `service_category` desconocida con 400.
- [x] `POST /leads` rechaza con 422 `company_size` fuera de `companySizes`, `message` con menos de 5 caracteres tras `trim` y `contact_name` de menos de 2 caracteres.
- [x] `POST /leads` normaliza el email a minúsculas antes de persistir.
- [x] `POST /leads` acepta `labs` y `academy` como consulta general (201, estado `recibido`).
- [x] `POST /leads` funciona sin token (endpoint público).

## 6. Casos de prueba (TDD Vanilla)

- `test_create_lead_persists_with_status_recibido`: Arrange: payload válido con email correcto. Act: `POST /leads`. Assert: 201, `status == "recibido"`, `assigned_agent_id is None`, el registro existe en BD.
- `test_create_lead_rejects_invalid_email`: Arrange: payload con `email="no-es-email"`. Act: `POST /leads`. Assert: 422 (validación Pydantic).
- `test_create_lead_rejects_unknown_service_category`: Arrange: payload con `service_category="otra-cosa"`. Act: `POST /leads`. Assert: 400.
- `test_create_lead_accepts_labs_and_academy_categories`: Arrange: payload con `service_category="labs"` (y luego `"academy"`). Act: `POST /leads`. Assert: 201, lead persistido con estado `recibido` como consulta general.
- `test_create_lead_rejects_unknown_company_size`: Arrange: payload con `company_size="Micro empresa"`. Act: `POST /leads`. Assert: 422.
- `test_create_lead_rejects_message_too_short`: Arrange: payload con `message="hola"` (4 caracteres tras trim). Act: `POST /leads`. Assert: 422.
- `test_create_lead_normalizes_email_to_lowercase`: Arrange: payload con `email="Cliente@Empresa.com"`. Act: `POST /leads`. Assert: el email persistido es `cliente@empresa.com`.
- `test_create_lead_rejects_contact_name_too_short`: Arrange: payload con `contact_name="A"` (1 carácter). Act: `POST /leads`. Assert: 422 (mínimo 2 caracteres).
- `test_create_lead_rejects_message_with_only_spaces`: Arrange: payload con `message="     "` (solo espacios). Act: `POST /leads`. Assert: 422 (tras `trim`, longitud 0 < 5).
- `test_create_lead_rejects_missing_required_fields`: Arrange: body sin `contact_name`/`email`/`company_size`/`message` (o `{}`). Act: `POST /leads`. Assert: 422 (campos requeridos ausentes).
- `test_create_lead_public_without_token`: Arrange: sin token. Act: `POST /leads` con payload válido. Assert: 201 (endpoint público, no requiere autenticación).
- `test_create_lead_creates_quote_params_versioned` (añadido 2026-10-01, decisión spec padre §5.3): Arrange: payload válido. Act: `POST /leads`. Assert: existe `quote_params` del lead con `version=1` y `params` con el mensaje estructurado (`source`, `message`, `company_size`).

## 7. Riesgos y consideraciones

- **Spam/abuso en `POST /leads`:** endpoint público. Considerar limitación de tasa por IP (p. ej., middleware simple o campo honeypot) en iteración posterior; mínimo, validación estricta de email y longitud de campos.
- **Datos personales:** el lead contiene PII (email, nombre, tamaño de empresa). Documentar retención y no exponerla en respuestas públicas.

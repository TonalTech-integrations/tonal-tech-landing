# 002-05 - Crear cotización manual (POST /admin/leads/{id}/quote)

- **Spec padre:** [002 - Sistema de leads y cotizaciones B2B](../../002-cotizacion-b2b.md) (secciones: 5.1, 5.2, 5.3, 5.5, 8.4, 6, 7)
- **Estado:** borrador
- **Fecha:** 2026-09-28
- **Tipo:** Backend
- **Dependencias:** 002-01 (el lead a cotizar se crea vía `POST /leads`); 002-04 (el lead debe estar en `en_revision` o `cotizado`, según la máquina de estados)
- **Suite de pruebas sugerida:** Sugerida: `backend/tests/test_leads_crear_cotizacion.py`

## 1. Descripción

Endpoint de administración `POST /admin/leads/{lead_id}/quote` que crea o actualiza la cotización manual de un lead (monto, moneda, vigencia, notas), delega en la interfaz `QuoteService` (implementación `ManualQuoteService`) y mueve el lead a `cotizado`. Los parámetros de cotización por servicio (`QuoteParams`) se almacenan como JSON versionado. El diseño desacoplado permite migrar a `AIQuoteService` en Fase 4 sin cambios estructurales.

## 2. Requisitos cubiertos

| ID padre | Requisito | Prioridad |
|----------|-----------|-----------|
| R6 | `POST /admin/leads/{id}/quote` para crear la cotización manual (monto, moneda, vigencia, notas) | Alta |
| R10 | Interfaz `QuoteService` desacoplada (`generate(lead, params) -> Quote`) con implementación manual | Media |
| R12 | Los parámetros de cotización por servicio (`QuoteParams`) se almacenan como JSON versionado | Media |
| R11 | Los endpoints `/admin/leads*` exigen JWT + `is_admin` (mismo patrón que `backend/routers/admin.py`) | Alta |

## 3. Diseño

**Modelo (5.1):**
- Tabla `quotes`: `id`, `lead_id` (único, 1 cotización activa por lead), `amount_cents`, `currency` (default `mxn`), `valid_until`, `notes`, `created_by`, `created_at`.
- Tabla `quote_params`: `id`, `lead_id`, `service_category`, `params` (JSON), `version` (versionado del esquema), `created_at`.

**Endpoint (5.2):** `POST /admin/leads/{lead_id}/quote` — administración (JWT + `is_admin`).
- Body: `{amount_cents, currency?, valid_until, notes?}`.
- Requiere lead en estado `en_revision` o `cotizado`; al crearla, el lead pasa a `cotizado`.
- Respuesta: 201 cotización creada (o 200 si se actualiza la existente).

**Interfaz de servicio (5.3):**

```python
# backend/services/quote_service.py
class QuoteService(Protocol):
    def generate(self, lead: Lead, params: QuoteParams) -> Quote: ...

class ManualQuoteService:
    """Fase manual: el agente humano define monto/vigencia vía POST /admin/leads/{id}/quote."""
    def generate(self, lead, params) -> Quote: ...
```

- El endpoint `POST /admin/leads/{id}/quote` delega en `ManualQuoteService` (hoy).
- En Fase 4 se intercambia la implementación por `AIQuoteService` sin cambiar endpoints ni modelo.
- `QuoteParams` es el contrato de entrada: hoy se llena con el mensaje estructurado del lead; en Fase 4 con las respuestas del diálogo de IA.

**Inyección del servicio (5.3, spec 008):** el endpoint recibe la implementación activa vía `Depends(get_quote_service)`; `get_quote_service` devuelve `ManualQuoteService` cuando `QUOTE_SERVICE=manual` (default) y `AIQuoteService` cuando `QUOTE_SERVICE=ai` (spec 008, sección 5.2). El endpoint depende de la interfaz `QuoteService`, nunca de una implementación concreta.

## 4. Especificación funcional (SDD)

- **Entrada:** `{amount_cents, currency?, valid_until, notes?}`.
- **Salida:** 201 cotización creada (o 200 si se actualiza la existente).
- **Reglas:** `amount_cents >= 0`; `valid_until` en el futuro; el lead debe estar en `en_revision` o `cotizado`; al crear/actualizar, el lead pasa a `cotizado`; delega en `QuoteService.generate`.
- **Casos borde:** lead en `recibido` → 400 ("El lead debe estar en revisión"); `amount_cents` negativo → 422; `valid_until` en el pasado → 422; cotización existente → se actualiza (no duplica).

## 5. Criterios de aceptación

- [ ] `POST /admin/leads/{id}/quote` crea la cotización y mueve el lead a `cotizado`.
- [ ] Existe `QuoteService` como interfaz y `ManualQuoteService` como implementación; el endpoint de cotización depende de la interfaz, no de la implementación.
- [ ] `QuoteParams` almacena los parámetros por servicio como JSON versionado.
- [ ] Los endpoints `/admin/leads*` devuelven 401 sin token (FastAPI `HTTPBearer` responde 401 sin credenciales (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima)) y 403 para usuario no admin.

## 6. Casos de prueba (TDD Vanilla)

- `test_create_quote_moves_lead_to_cotizado`: Arrange: lead en `en_revision`. Act: `POST /admin/leads/{id}/quote` con monto y vigencia válidos. Assert: 201, cotización creada, lead en `cotizado`.
- `test_create_quote_rejected_when_lead_recibido`: Arrange: lead en `recibido`. Act: `POST /admin/leads/{id}/quote`. Assert: 400.
- `test_create_quote_rejects_negative_amount`: Arrange: lead en `en_revision`. Act: quote con `amount_cents=-1`. Assert: 422.
- `test_create_quote_accepts_zero_amount`: Arrange: lead en `en_revision`. Act: quote con `amount_cents=0`. Assert: 201 (el padre 8.4 define `amount_cents >= 0`, por lo que 0 es válido; solo el negativo es 422).
- `test_create_quote_updates_existing_quote_not_duplicates`: Arrange: lead con cotización existente. Act: `POST /admin/leads/{id}/quote` de nuevo. Assert: 200 y una sola fila en `quotes` para ese lead.
- `test_quote_service_interface_swappable`: Arrange: `ManualQuoteService` registrado. Act: invocar el endpoint de cotización. Assert: delega en la interfaz `QuoteService` (inyección por dependencia), permitiendo reemplazar por `AIQuoteService` sin cambios de endpoint.
- `test_create_quote_404_when_lead_not_found`: Arrange: `lead_id` inexistente. Act: `POST /admin/leads/{id}/quote`. Assert: 404.
- `test_create_quote_rejects_invalid_currency`: Arrange: lead en `en_revision`. Act: quote con `currency="xyz"` (código no soportado; la lista de monedas válidas la define el backend, default `mxn`). Assert: 422.
- `test_create_quote_rejects_past_valid_until`: Arrange: lead en `en_revision`. Act: quote con `valid_until` en el pasado. Assert: 422.
- `test_create_quote_requires_auth`: Arrange: sin token. Act: `POST /admin/leads/{id}/quote`. Assert: 401 (FastAPI `HTTPBearer` responde 401 sin credenciales (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima)).
- `test_create_quote_requires_admin`: Arrange: token de usuario normal. Act: `POST /admin/leads/{id}/quote`. Assert: 403.

## 7. Riesgos y consideraciones

- **Fase 4 (IA):** la calidad de la cotización por IA depende de parámetros de BD por servicio; `QuoteParams` debe versionarse para no romper cotizaciones históricas.

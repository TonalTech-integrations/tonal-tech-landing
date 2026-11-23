# 002-03 - Detalle de lead (admin)

- **Spec padre:** [002 - Sistema de leads y cotizaciones B2B](../../002-cotizacion-b2b.md) (secciones: 5.1, 5.2, 6)
- **Estado:** implementada (2026-10-01)
- **Fecha:** 2026-09-28
- **Tipo:** Backend
- **Dependencias:** 002-01 (el lead consultado se crea vía `POST /leads`); 002-05 (la cotización y los parámetros que se exponen se crean vía `POST /admin/leads/{id}/quote`)
- **Suite de pruebas sugerida:** Sugerida: `backend/tests/test_leads_detalle_admin.py`

## 1. Descripción

Endpoint de administración `GET /admin/leads/{lead_id}` que devuelve el detalle completo de un lead: sus datos, su cotización (`quotes`) y sus parámetros de cotización (`quote_params`). Exige JWT + `is_admin`.

## 2. Requisitos cubiertos

| ID padre | Requisito | Prioridad |
|----------|-----------|-----------|
| R4 | `GET /admin/leads/{id}` con detalle del lead, su cotización y parámetros | Alta |
| R11 | Los endpoints `/admin/leads*` exigen JWT + `is_admin` (mismo patrón que `backend/routers/admin.py`) | Alta |

## 3. Diseño

**Endpoint (5.2):** `GET /admin/leads/{lead_id}` — administración (JWT + `is_admin`).
- Descripción: detalle: lead + quote + quote_params.

**Modelo relacionado (5.1):** tablas `quotes` (1 cotización activa por lead) y `quote_params` (parámetros por servicio como JSON versionado).

## 4. Especificación funcional (SDD)

- **Entrada:** `lead_id` (int) en path; token JWT + `is_admin`.
- **Salida:** `{lead, quote, quote_params}` donde `quote` y `quote_params` son `null` si el lead no tiene cotización.
- **Reglas:** solo admins; el detalle incluye lead + quote + quote_params (5.2).
- **Casos borde:** lead inexistente → 404; lead sin cotización → `quote: null` y `quote_params` presente (desde 002-01 todo lead nace con `quote_params` v1, decisión §5.3 del padre); un lead sin fila `quote_params` (legado) devuelve ambos `null` (no 404).

## 5. Criterios de aceptación

- [x] Los endpoints `/admin/leads*` devuelven 401 sin token (FastAPI `HTTPBearer` responde 401 sin credenciales (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima)) y 403 para usuario no admin.
- [x] `GET /admin/leads/{id}` devuelve `{lead, quote, quote_params}`; 404 si el lead no existe; `quote` es `null` si el lead no tiene cotización (con `quote_params` presente, creado en 002-01); ambos `null` si el lead no tiene fila `quote_params` (legado).

## 6. Casos de prueba (TDD Vanilla)

- `test_get_lead_detail_returns_lead_quote_and_params`: Arrange: lead con cotización y `quote_params` creados (002-01 + 002-05). Act: `GET /admin/leads/{id}`. Assert: 200 con `{lead, quote, quote_params}` completos.
- `test_get_lead_detail_404_when_not_found`: Arrange: `lead_id` inexistente. Act: `GET /admin/leads/{id}`. Assert: 404.
- `test_get_lead_detail_quote_null_when_no_quote`: Arrange: lead sin cotización (con `quote_params` v1 creado en 002-01). Act: `GET /admin/leads/{id}`. Assert: 200 con `quote is None` y `quote_params` presente con `version=1` (corregido 2026-10-01 por la decisión §5.3 del padre).
- `test_get_lead_detail_without_quote_params_returns_nulls` (añadido 2026-10-01, caso legado): Arrange: lead sin fila `quote_params` (eliminada manualmente en el Arrange). Act: `GET /admin/leads/{id}`. Assert: 200 con `quote is None` y `quote_params is None`.
- `test_get_lead_detail_requires_auth`: Arrange: sin token. Act: `GET /admin/leads/{id}`. Assert: 401 (FastAPI `HTTPBearer` responde 401 sin credenciales (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima)).
- `test_get_lead_detail_requires_admin`: Arrange: token de usuario normal. Act: `GET /admin/leads/{id}`. Assert: 403.

## 7. Riesgos y consideraciones

- **Dependencia con 005:** la UI de gestión de leads se construye en la spec 005; esta spec solo define API y modelo.

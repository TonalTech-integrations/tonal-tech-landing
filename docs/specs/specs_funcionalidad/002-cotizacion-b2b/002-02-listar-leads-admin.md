# 002-02 - Listar leads (admin)

- **Spec padre:** [002 - Sistema de leads y cotizaciones B2B](../../002-cotizacion-b2b.md) (secciones: 5.2, 8.2, 6, 7)
- **Estado:** implementada (2026-10-01)
- **Fecha:** 2026-09-28
- **Tipo:** Backend
- **Dependencias:** 002-01 (los leads listados se crean vía `POST /leads`)
- **Suite de pruebas sugerida:** Sugerida: `backend/tests/test_leads_listar_admin.py`

## 1. Descripción

Endpoint de administración `GET /admin/leads` que lista los leads con filtros combinables (estado, categoría, rango de fechas), paginación y orden por `created_at` descendente. Exige JWT + `is_admin` (mismo patrón que `backend/routers/admin.py`). Es el endpoint que el dashboard admin (spec 005) consumirá para gestionar leads.

## 2. Requisitos cubiertos

| ID padre | Requisito | Prioridad |
|----------|-----------|-----------|
| R3 | `GET /admin/leads` con filtros (estado, categoría, rango de fechas) y orden por fecha descendente | Alta |
| R11 | Los endpoints `/admin/leads*` exigen JWT + `is_admin` (mismo patrón que `backend/routers/admin.py`) | Alta |

## 3. Diseño

**Endpoint (5.2):** `GET /admin/leads` — administración (JWT + `is_admin`, vía `require_admin` de `backend/routers/admin.py`).
- Query: `status?`, `service_category?`, `from?`, `to?`, `page?`, `page_size?` (default 20).
- Orden: `created_at` desc.
- Salida: `{items: [LeadSummary...], total, page, page_size}`.

**Schema `LeadSummary` (5.2):** `{id, service_category, contact_name, email, company_size, status, assigned_agent_id, created_at, updated_at}`. No incluye `message` (solo va en el detalle de 002-03).

**Nota (5.2):** el router nuevo `backend/routers/leads.py` se registra en `backend/main.py` con prefijo `/leads` y `/admin/leads` (o un solo router con ambos grupos). Los endpoints de administración reutilizan `require_admin` para no duplicar lógica.

## 4. Especificación funcional (SDD)

- **Entrada:** query `status?`, `service_category?`, `from?`, `to?`, `page?`, `page_size?`.
- **Salida:** `{items: [LeadSummary...], total, page, page_size}`.
- **Reglas:** solo admins; filtros combinables; `from`/`to` filtran por `created_at`; orden `created_at` desc; `page_size` máx. 100.
- **Casos borde:** filtros sin resultados (lista vacía, `total=0`); fechas inválidas → 422; `page` fuera de rango → lista vacía, no error.

## 5. Criterios de aceptación

- [x] Un lead creado desde la landing aparece en `GET /admin/leads` sin reiniciar el backend.
- [x] Los endpoints `/admin/leads*` devuelven 401 sin token (FastAPI `HTTPBearer` responde 401 sin credenciales (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima)) y 403 para usuario no admin.
- [x] `GET /admin/leads` soporta filtros combinables (estado, categoría, rango `from`/`to`) y paginación (`page`/`page_size` con `total`); `page_size` máx. 100.

## 6. Casos de prueba (TDD Vanilla)

- `test_list_leads_requires_admin`: Arrange: token de usuario normal. Act: `GET /admin/leads`. Assert: 403.
- `test_list_leads_requires_auth`: Arrange: sin token. Act: `GET /admin/leads`. Assert: 401 (FastAPI `HTTPBearer` responde 401 sin credenciales (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima)).
- `test_list_leads_filters_by_status_and_category`: Arrange: 3 leads (2 `recibido`, 1 `cotizado`; 1 de `ciberseguridad`). Act: `GET /admin/leads?status=recibido&service_category=ciberseguridad`. Assert: solo el lead que cumple ambos filtros.
- `test_list_leads_orders_by_created_at_desc`: Arrange: 2 leads con fechas distintas. Act: `GET /admin/leads`. Assert: el más reciente aparece primero.
- `test_list_leads_filters_by_date_range`: Arrange: 2 leads con `created_at` distintos (uno dentro y uno fuera del rango). Act: `GET /admin/leads?from=...&to=...`. Assert: solo el lead dentro del rango.
- `test_list_leads_paginates_with_total`: Arrange: 25 leads. Act: `GET /admin/leads?page=2&page_size=10`. Assert: 10 items, `total=25`, `page=2`, `page_size=10`.
- `test_list_leads_rejects_page_size_over_100`: Arrange: token admin. Act: `GET /admin/leads?page_size=101`. Assert: 422 (decisión confirmada: el padre 8.2 fija máx. 100; `page_size > 100` → 422).
- `test_list_leads_empty_result_with_total_zero`: Arrange: sin leads (o filtro sin coincidencias). Act: `GET /admin/leads`. Assert: `items=[]`, `total=0`.
- `test_list_leads_rejects_invalid_date`: Arrange: token admin. Act: `GET /admin/leads?from=no-es-fecha`. Assert: 422.
- `test_list_leads_page_out_of_range_returns_empty` (añadido 2026-10-01, caso borde §4): Arrange: 3 leads, se pide `page=5&page_size=20`. Act: `GET /admin/leads`. Assert: 200 con `items=[]` y `total=3` (página fuera de rango devuelve lista vacía, no error).

## 7. Riesgos y consideraciones

- **Dependencia con 005:** la UI de gestión de leads se construye en la spec 005; esta spec solo define API y modelo. El dashboard no debe bloquearse si 005 se retrasa (se puede probar con curl/Postman).

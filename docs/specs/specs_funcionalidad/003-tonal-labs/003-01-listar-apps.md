# 003-01 - Listar apps de Labs (GET /labs/apps)

- **Spec padre:** [003 - Tonal-Tech Labs: listado de apps móviles, detalle, descarga y trailer](../../003-tonal-labs.md) (secciones: 5.1, 5.2, 5.4, 8.1, 6, 7)
- **Estado:** borrador
- **Fecha:** 2026-09-28
- **Tipo:** Backend
- **Dependencias:** Ninguna
- **Suite de pruebas sugerida:** Sugerida: `backend/tests/test_labs_listar_apps.py`

## 1. Descripción

Modelo de datos `App` (backend) con seed inicial y endpoint público `GET /labs/apps` que devuelve solo apps activas, ordenadas por `published_at` desc, con `is_free` derivado (`price_cents is None or price_cents == 0`). Los datos viven en el backend (decisión justificada en 5.4), no en `lib/` estático.

## 2. Requisitos cubiertos

| ID padre | Requisito | Prioridad |
|----------|-----------|-----------|
| R1 | `GET /labs/apps` público devuelve solo apps activas, ordenadas por fecha de publicación desc | Alta |
| R3 | El modelo `App` incluye precio opcional (`price_cents` nullable) para apps gratuitas o de pago | Alta |
| R7 | Los datos viven en el backend (decisión justificada en 5.4), no en `lib/` estático | Alta |

## 3. Diseño

**Modelo (5.1, backend/services/persistence.py, tabla `apps`):** `id`, `slug` (unique), `name`, `tagline`, `description`, `category`, `icon_url`, `screenshots` (JSON, opcional), `price_cents` (nullable; `NULL` o `0` = gratuita; > 0 = de pago), `currency` (default `mxn`), `download_url`, `youtube_video_id`, `is_active` (default `True`), `published_at`, `created_at`/`updated_at`.

**Seed inicial (5.1):** 2–3 apps de ejemplo (una gratuita, una de pago) para desarrollo; el contenido real lo define el equipo.

**Endpoint (5.2):** `GET /labs/apps` — pública.
- Lista `AppSummary` de apps activas, orden `published_at` desc.
- `is_free` se deriva: `price_cents is None or price_cents == 0`.
- No se exponen campos internos (`is_active`, `created_at`/`updated_at`) ni campos del detalle (`description`, `screenshots`, `download_url`, `youtube_video_id`) en la respuesta pública.
- Router nuevo `backend/routers/labs.py`, registrado en `backend/main.py`.

**Schema `AppSummary` (campos exactos de la respuesta, 5.2):**

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | |
| `slug` | str | Identificador legible (ej. `tonal-inventory`) |
| `name` | str | |
| `tagline` | str | |
| `category` | str | Ej. `logistica`, `educacion`, `salud` (libre) |
| `icon_url` | str | |
| `price_cents` | int \| null | `NULL` o `0` = gratuita; > 0 = de pago |
| `currency` | str | Default `mxn` |
| `is_free` | bool | Derivado: `price_cents is None or price_cents == 0` |

**Filtro `category` (R11 del padre, decisión confirmada):** el padre añade el requisito R11 ("`GET /labs/apps` acepta el query opcional `category` para filtrar por categoría") con comparación case-sensitive contra el valor de `category` del seed (categorías en minúsculas); categoría sin resultados → lista vacía (no 400).

## 4. Especificación funcional (SDD)

- **Entrada:** ninguna (query opcional `category` para filtrar; ver 3).
- **Salida:** 200 `{items: [AppSummary...]}`.
- **Reglas:** solo `is_active=True`; orden `published_at` desc; `is_free = price_cents is None or price_cents == 0`; no expone `is_active`, `created_at`/`updated_at` ni campos del detalle (`download_url`, `youtube_video_id`, `description`, `screenshots`).
- **Casos borde:** sin apps activas → `items: []` (no error); filtro `category` sin resultados → lista vacía; categoría inexistente → lista vacía (no 400); `price_cents` nulo o 0 → `is_free=true`; `price_cents` > 0 → `is_free=false` conservando el precio.

## 5. Criterios de aceptación

- [ ] `GET /labs/apps` devuelve solo apps activas ordenadas por `published_at` desc.
- [ ] Una app con `price_cents` nulo/0 se marca `is_free=true`; una con `price_cents>0` se marca `is_free=false` y conserva su precio.
- [ ] Sin apps activas → 200 con `items: []` (no error).
- [ ] El filtro opcional `category` devuelve solo las apps de esa categoría; sin resultados → `items: []` (no 400).
- [ ] El listado no expone campos internos (`is_active`, `created_at`/`updated_at`) ni campos del detalle (`download_url`, `youtube_video_id`, `description`, `screenshots`).
- [ ] No existe catálogo de apps duplicado en `lib/` (los datos viven solo en backend).

## 6. Casos de prueba (TDD Vanilla)

- `test_list_apps_returns_only_active_ordered_by_published_at_desc`: Arrange: 3 apps (1 inactiva), fechas distintas. Act: `GET /labs/apps`. Assert: 2 apps, la más reciente primero, sin la inactiva.
- `test_list_apps_marks_free_when_price_null_or_zero`: Arrange: app con `price_cents=None` y app con `price_cents=0`. Act: `GET /labs/apps`. Assert: ambas con `is_free=True`.
- `test_list_apps_marks_paid_when_price_positive`: Arrange: app con `price_cents=9900`. Act: `GET /labs/apps`. Assert: `is_free=False`, `price_cents=9900`.
- `test_list_apps_returns_empty_when_no_active_apps`: Arrange: solo apps inactivas. Act: `GET /labs/apps`. Assert: 200 con `items: []`.
- `test_list_apps_filters_by_category`: Arrange: apps de 2 categorías. Act: `GET /labs/apps?category=logistica`. Assert: solo las de esa categoría.
- `test_list_apps_filters_by_category_no_results_returns_empty`: Arrange: apps de categoría `logistica`. Act: `GET /labs/apps?category=salud`. Assert: 200 con `items: []`.
- `test_list_apps_does_not_expose_internal_fields`: Arrange: app activa con `download_url`, `youtube_video_id` e `is_active=True`. Act: `GET /labs/apps`. Assert: los items solo incluyen los campos de `AppSummary` (no `download_url`, `youtube_video_id`, `description`, `screenshots`, `is_active`, `created_at`/`updated_at`).

## 7. Riesgos y consideraciones

- **`download_url`:** es un enlace externo; validar formato URL en el modelo (Pydantic `HttpUrl`) para evitar enlaces rotos.
- **Dependencia con 005/006:** el CRUD de apps (005) y las métricas de Labs (006) consumen este modelo; mantener `slug` estable desde el inicio.

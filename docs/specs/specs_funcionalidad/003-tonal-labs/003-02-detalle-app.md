# 003-02 - Detalle de app (GET /labs/apps/{id})

- **Spec padre:** [003 - Tonal-Tech Labs: listado de apps móviles, detalle, descarga y trailer](../../003-tonal-labs.md) (secciones: 5.2, 8.2, 6)
- **Estado:** borrador
- **Fecha:** 2026-09-28
- **Tipo:** Backend
- **Dependencias:** 003-01 (el modelo `App` y el seed definidos en 003-01)
- **Suite de pruebas sugerida:** Sugerida: `backend/tests/test_labs_detalle_app.py`

## 1. Descripción

Endpoint público `GET /labs/apps/{app_id}` que devuelve el detalle completo de una app activa (descripción, capturas, precio, link de descarga y trailer de YouTube) o 404 si no existe o está inactiva.

## 2. Requisitos cubiertos

| ID padre | Requisito | Prioridad |
|----------|-----------|-----------|
| R2 | `GET /labs/apps/{id}` público devuelve el detalle completo de la app o 404 | Alta |
| R4 | El detalle incluye link de descarga (`download_url`) y trailer de YouTube (`youtube_video_id`) | Alta |

## 3. Diseño

**Endpoint (5.2):** `GET /labs/apps/{app_id}` — pública.
- Detalle `AppDetail` (todo lo anterior + description, screenshots, download_url, youtube_video_id) o 404.
- No se exponen campos internos (`is_active`, `created_at` internos) en la respuesta pública.

## 4. Especificación funcional (SDD)

- **Entrada:** `app_id` (int).
- **Salida:** 200 `AppDetail` con todos los campos públicos.
- **Reglas:** app inexistente o `is_active=False` → 404 "App no encontrada".
- **Casos borde:** `app_id` no numérico → 422; app inactiva → 404 (no revela existencia); `screenshots` vacío → lista vacía en la respuesta.

## 5. Criterios de aceptación

- [ ] `GET /labs/apps/{id}` devuelve el detalle completo; 404 para id inexistente o app inactiva.
- [ ] `GET /labs/apps/{id}` con `app_id` no numérico → 422.
- [ ] El detalle no expone campos internos (`is_active`, `created_at`/`updated_at`).

## 6. Casos de prueba (TDD Vanilla)

- `test_get_app_detail_returns_full_info`: Arrange: app activa con screenshots, download_url y youtube_video_id. Act: `GET /labs/apps/{id}`. Assert: 200 con todos los campos.
- `test_get_app_detail_404_for_unknown_id`: Arrange: id inexistente. Act: `GET /labs/apps/99999`. Assert: 404.
- `test_get_app_detail_404_for_inactive_app`: Arrange: app con `is_active=False`. Act: `GET /labs/apps/{id}`. Assert: 404.
- `test_get_app_detail_rejects_non_numeric_id`: Arrange: `GET /labs/apps/abc`. Act: petición. Assert: 422.
- `test_get_app_detail_does_not_expose_internal_fields`: Arrange: app activa. Act: `GET /labs/apps/{id}`. Assert: la respuesta incluye los campos públicos de `AppDetail` (`description`, `screenshots`, `download_url`, `youtube_video_id`) y NO incluye `is_active`, `created_at` ni `updated_at`.

## 7. Riesgos y consideraciones

- **404 no revela existencia:** app inactiva e id inexistente responden el mismo 404 "App no encontrada" para no filtrar apps desactivadas.
- **`screenshots` vacío:** la respuesta incluye `screenshots: []` (lista vacía, no `null`).
- **Validación de `app_id`:** FastAPI valida el path param como `int`; un valor no numérico produce 422 antes de tocar la BD.
- **`download_url`:** enlace externo; validar formato URL en el modelo (Pydantic `HttpUrl`) para evitar enlaces rotos (se cubre en 003-01).
- **YouTube:** el embed depende de disponibilidad del video; si `youtube_video_id` es inválido, el iframe muestra error de YouTube (no rompe la página) — se cubre en 003-04.

# 006 - Métricas de acceso (tracking de visitas por sección)

- **Estado:** borrador
- **Fecha:** 2026-09-24
- **Autor:** Equipo Tonal-Tech

## 1. Resumen

La visión (FUNCIONALIDAD.md) pide que el dashboard admin muestre **métricas de acceso** y permita saber **a qué sección entran más los usuarios**. Hoy no existe ningún tracking de visitas en backend ni frontend (grep `metric/track/visit/analytics` en backend = 0 resultados) — gap Total (V11/V12 del spec 001).

Esta spec define el modelo de datos `PageView`, el endpoint público de registro `POST /metrics/page-view`, los endpoints de consulta admin `GET /admin/metrics` y `GET /admin/metrics/sections`, el hook de frontend `usePageView(section)` que registra la visita al montar cada sección, y la visualización en el dashboard admin (spec 005).

## 2. Objetivos

- Registrar una visita por cada vista de sección (landing, academy, labs, curso, éxito de pago, etc.).
- Responder "a qué sección entran más los usuarios" con agregados por sección.
- Proveer series temporales (visitas por día) para detectar tendencias.
- Integrar la visualización en el dashboard admin (005) sin librerías de charts pesadas.
- Mantener el tracking ligero y no intrusivo (fire-and-forget, sin bloquear la UI).

## 3. Alcance

### Incluye
- Modelo `PageView` (backend) con sección, ruta, usuario opcional, sesión, referrer, user-agent y fecha.
- `POST /metrics/page-view` público (registro).
- `GET /admin/metrics` y `GET /admin/metrics/sections` (consulta admin).
- Hook `usePageView(section)` y su integración en las páginas/secciones principales.
- Visualización en `components/admin/metrics-panel.tsx` (spec 005).
- Especificación SDD + casos TDD Vanilla.

### Excluye
- Analytics de eventos de negocio (compras, inscripciones) — esos datos ya viven en `purchases`/`enrollments`; aquí solo navegación.
- Tracking de clics individuales (solo vistas de sección).
- Herramientas externas (Google Analytics, Vercel Analytics — ya existe `@vercel/analytics` en `package.json`, pero no sustituye el dato propio del backend).
- Funnel/embudos de conversión complejos (iteración posterior).

## 4. Requisitos

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| R1 | `POST /metrics/page-view` público registra una vista con sección y ruta | Alta |
| R2 | El registro es fire-and-forget: el frontend no bloquea ni espera la respuesta | Alta |
| R3 | `GET /admin/metrics` devuelve totales: visitas totales, por día (últimos 30 días) y por sección | Alta |
| R4 | `GET /admin/metrics/sections` devuelve el ranking de secciones (la que más visitas tiene primero) | Alta |
| R5 | Los endpoints de consulta exigen JWT + `is_admin` | Alta |
| R6 | `usePageView(section)` registra la visita al montar la sección, una sola vez por montaje | Alta |
| R7 | Secciones definidas: `landing`, `academy`, `labs`, `course`, `success`, `admin`, `other` | Media |
| R8 | El modelo captura `user_id` si hay sesión (opcional) y `session_id` para visitas anónimas | Media |
| R9 | `metrics-panel` (005) muestra totales, ranking por sección y visitas por día | Media |
| R10 | El endpoint de registro tolera errores silenciosamente (no rompe la página) | Media |

## 5. Diseño / Arquitectura

### 5.1 Modelo de datos (backend/services/persistence.py)

**Tabla `page_views`**

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | |
| `section` | str | Enum: `landing`, `academy`, `labs`, `course`, `success`, `admin`, `other` |
| `path` | str | Ruta visitada (ej. `/academy`, `/labs`, `/courses/plc-industrial`) |
| `user_id` | int FK users.id | Nullable; se llena si el token JWT es válido |
| `session_id` | str | UUID generado en cliente (localStorage) para visitas anónimas |
| `referrer` | str | Nullable; `document.referrer` |
| `user_agent` | str | Nullable; `navigator.userAgent` (truncado) |
| `created_at` | datetime | Índice para agregados por día |

**Nota de privacidad:** no se almacena IP; `user_agent` se trunca (p. ej. 200 chars) y no se usa para identificación.

### 5.2 Endpoints

| Método | Ruta | Autenticación | Descripción |
|--------|------|---------------|-------------|
| POST | `/metrics/page-view` | Pública (JWT opcional) | Body: `{section, path, session_id?, referrer?}`. Registra la vista; responde 204 (sin contenido) para minimizar payload |
| GET | `/admin/metrics` | JWT + `is_admin` | `{total_views, views_by_day: [{date, count}], views_by_section: [{section, count}]}` (últimos 30 días) |
| GET | `/admin/metrics/sections` | JWT + `is_admin` | `{items: [{section, count}]}` ordenado desc (ranking) |

- Router nuevo `backend/routers/metrics.py`, registrado en `backend/main.py`.
- `POST /metrics/page-view` valida `section` contra el enum (422 si no); `path` obligatorio.
- Si el header `Authorization` trae un token válido, se asocia `user_id`; si es inválido/ausente, se registra como anónimo (nunca 401 en el registro).

### 5.3 Frontend: hook `usePageView`

```ts
// lib/use-page-view.ts
export function usePageView(section: Section) {
  // Al montar (una vez), genera/lee session_id de localStorage y llama
  // trackPageView({ section, path: window.location.pathname, session_id, referrer })
  // fire-and-forget: .catch(() => {}) — nunca rompe la UI
}
```

**Integración (una llamada por montaje):**

| Componente / página | Sección |
|---------------------|---------|
| `app/page.tsx` (landing) | `landing` |
| `app/academy/page.tsx` | `academy` |
| `app/labs/page.tsx` (spec 003) | `labs` |
| `CourseViewer` (detalle de curso) | `course` (path `/courses/{id}`) |
| `app/success/page.tsx` | `success` |
| `app/admin/page.tsx` (spec 005) | `admin` |

- `lib/api.ts`: añadir `trackPageView(payload)` (sin JWT) y `getAdminMetrics()`, `getAdminMetricsBySection()` (con JWT).

### 5.4 Visualización en el dashboard (spec 005)

`components/admin/metrics-panel.tsx`:

- **Totales:** tarjeta con `total_views` (últimos 30 días).
- **Ranking por sección:** lista ordenada con barras CSS proporcionales (sin librería de charts): `landing ████████ 1200`, `academy ██████ 800`, etc.
- **Visitas por día:** mini-gráfico de barras CSS con los últimos 14 días (etiqueta de fecha + altura proporcional).
- Estados: cargando, error (reintento), vacío ("Aún no hay métricas").

## 6. Criterios de aceptación

- [ ] `POST /metrics/page-view` registra la vista y responde 204; sección inválida → 422.
- [ ] El registro funciona sin token (anónimo) y con token (asocia `user_id`); nunca responde 401.
- [ ] `GET /admin/metrics` devuelve totales, visitas por día (30 días) y por sección; exige admin.
- [ ] `GET /admin/metrics/sections` devuelve el ranking desc; exige admin.
- [ ] `usePageView` registra una sola vista por montaje y no bloquea la UI (errores silenciosos).
- [ ] Landing, Academy, Labs, detalle de curso, success y admin registran su sección.
- [ ] `metrics-panel` muestra totales, ranking y visitas por día.

## 7. Riesgos y consideraciones

- **Ruido/abuso:** el endpoint de registro es público; considerar limitación de tasa por `session_id`/IP en iteración posterior (mínimo: validar longitud de campos y sección).
- **Privacidad:** no guardar IP; truncar `user_agent`; `session_id` es un UUID anónimo, no un identificador personal. Documentar retención de datos.
- **Doble registro:** con React StrictMode (dev) los efectos se montan dos veces; `usePageView` debe protegerse con un ref para registrar una sola vez por montaje real (en producción no aplica, pero las pruebas deben cubrirlo).
- **Fire-and-forget:** el `.catch(() => {})` evita romper la UI, pero también oculta fallos del backend; en desarrollo se puede loguear en consola detrás de un flag.
- **Dependencia con 005:** la visualización vive en el dashboard; si 005 se retrasa, los endpoints se prueban con curl/Postman.
- **Zona horaria:** los agregados por día deben usar la zona del servidor (o UTC) de forma consistente; documentar la elección (UTC) para evitar saltos de fechas.

## 8. Especificación funcional (SDD)

### 8.1 `POST /metrics/page-view` (público)

- **Entrada:** `{section, path, session_id?, referrer?}`.
- **Salida:** 204 sin cuerpo.
- **Reglas:** `section` ∈ enum (422 si no); `path` obligatorio no vacío (422); `session_id` opcional (si falta, se genera en servidor); si hay token JWT válido → `user_id`; token inválido/ausente → anónimo (nunca 401); `user_agent` se toma del header y se trunca.
- **Casos borde:** sección desconocida → 422; `path` vacío → 422; payload con campos extra → se ignoran; token corrupto → se registra anónimo; `referrer` muy largo → truncar.

### 8.2 `GET /admin/metrics` (admin)

- **Entrada:** query `days?` (default 30, máx 90).
- **Salida:** `{total_views, views_by_day: [{date, count}], views_by_section: [{section, count}]}`.
- **Reglas:** solo admins; `views_by_day` incluye solo días con datos (o días completos con 0 — se elige **solo días con datos** para simplicidad); `views_by_section` ordenado desc.
- **Casos borde:** sin datos → `total_views=0`, listas vacías; `days` inválido (>90 o <1) → 422; sin token → 401 (`HTTPBearer` sin credenciales responde 401 (comportamiento de FastAPI >= 0.122; el backend fija esta versión mínima)); no admin → 403.

### 8.3 `GET /admin/metrics/sections` (admin)

- **Entrada:** ninguna.
- **Salida:** `{items: [{section, count}]}` ordenado desc.
- **Reglas:** solo admins; incluye solo secciones con al menos una vista.
- **Casos borde:** sin datos → `items: []`; empate de conteos → orden estable por nombre de sección.

### 8.4 `usePageView` (frontend)

- **Entrada:** `section`.
- **Salida:** ninguna (efecto secundario).
- **Reglas:** al montar, una sola vez (ref de guardia), lee/crea `session_id` en localStorage, llama `trackPageView` con `path` actual y `referrer`; errores silenciosos.
- **Casos borde:** StrictMode (doble montaje en dev) → una sola llamada; `localStorage` no disponible → generar `session_id` en memoria; navegación SPA sin recarga → el hook se monta por página, registra por montaje.

## 9. Casos de prueba (TDD Vanilla)

- `test_track_page_view_returns_204_and_persists`: Arrange: payload válido. Act: `POST /metrics/page-view`. Assert: 204 y una fila en `page_views` con la sección y path.
- `test_track_page_view_rejects_unknown_section`: Arrange: `section="otra"`. Act: `POST /metrics/page-view`. Assert: 422.
- `test_track_page_view_rejects_empty_path`: Arrange: `path=""`. Act: endpoint. Assert: 422.
- `test_track_page_view_anonymous_without_token`: Arrange: sin header Authorization. Act: endpoint. Assert: 204, `user_id is None`.
- `test_track_page_view_associates_user_with_valid_token`: Arrange: token JWT válido. Act: endpoint. Assert: 204, `user_id` del usuario.
- `test_track_page_view_anonymous_with_corrupt_token`: Arrange: token corrupto. Act: endpoint. Assert: 204 (no 401), `user_id is None`.
- `test_track_page_view_truncates_long_user_agent`: Arrange: header User-Agent de 5000 chars. Act: endpoint. Assert: 204 y `user_agent` truncado (≤ 200).
- `test_admin_metrics_requires_admin`: Arrange: token de usuario normal. Act: `GET /admin/metrics`. Assert: 403.
- `test_admin_metrics_returns_totals_and_aggregates`: Arrange: 5 vistas (3 `landing`, 2 `academy`) en 2 días. Act: `GET /admin/metrics`. Assert: `total_views=5`, `views_by_section` con `landing:3, academy:2`, `views_by_day` con 2 entradas.
- `test_admin_metrics_empty_when_no_data`: Arrange: sin vistas. Act: `GET /admin/metrics`. Assert: `total_views=0`, listas vacías.
- `test_admin_metrics_rejects_days_out_of_range`: Arrange: `days=999`. Act: `GET /admin/metrics?days=999`. Assert: 422.
- `test_admin_metrics_sections_returns_ranking_desc`: Arrange: vistas con conteos `academy=5, landing=10`. Act: `GET /admin/metrics/sections`. Assert: `landing` primero, luego `academy`.
- `test_use_page_view_tracks_once_on_mount`: Arrange: mock de `trackPageView`. Act: montar componente con `usePageView("landing")` (simulando StrictMode con doble efecto). Assert: `trackPageView` invocado una sola vez.
- `test_use_page_view_does_not_throw_on_failure`: Arrange: mock de `trackPageView` rechazando. Act: montar. Assert: no se propaga excepción; la UI se renderiza normal.
- `test_use_page_view_sends_path_and_session_id`: Arrange: mock de `trackPageView`, `window.location.pathname="/academy"`. Act: montar con `usePageView("academy")`. Assert: payload con `section="academy"`, `path="/academy"`, `session_id` no vacío.
- `test_metrics_panel_renders_totals_ranking_and_daily`: Arrange: mock de `getAdminMetrics` y `getAdminMetricsBySection` con datos. Act: render `metrics-panel`. Assert: total visible, ranking ordenado y barras por día presentes.
- `test_metrics_panel_shows_empty_state`: Arrange: mocks resolviendo sin datos. Act: render. Assert: mensaje "Aún no hay métricas".

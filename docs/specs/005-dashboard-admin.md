# 005 - Dashboard oculto de administradores (UI)

- **Estado:** borrador
- **Fecha:** 2026-09-24
- **Autor:** Equipo Tonal-Tech

## 1. Resumen

La visión (FUNCIONALIDAD.md) pide un **dashboard oculto para administradores** que sirva para agregar cursos, gestionar el tipo pago/gratuito, ver métricas de acceso y saber a qué sección entran más los usuarios. Hoy el backend ya expone endpoints `/admin/*` (CRUD de cursos/módulos/lecciones, enrollments manuales, protegidos por `is_admin`), pero **no existe ninguna UI** en `app/` (grep `admin` en `app/` = 0 resultados) — gap Total en UI (V9/V10 del spec 001).

Esta spec construye la **UI del dashboard** en la ruta `/admin`: protegida por JWT + `is_admin`, con secciones de Cursos (incluyendo tipo pago/gratuito), Módulos, Lecciones, Enrollments, Leads/Cotizaciones (spec 002) y Métricas (spec 006). Reutiliza los endpoints `/admin/*` existentes y especifica los que faltan.

## 2. Objetivos

- Crear la ruta `/admin` con protección de acceso (JWT + `is_admin`).
- Proveer CRUD visual de cursos (incluyendo el campo `is_free` de la spec 004), módulos y lecciones.
- Proveer gestión de enrollments manuales (otorgar/revocar).
- Proveer la vista de leads/cotizaciones consumiendo los endpoints de la spec 002.
- Proveer la vista de métricas consumiendo los endpoints de la spec 006.
- Reutilizar los endpoints `/admin/*` existentes; especificar los que falten.

## 3. Alcance

### Incluye
- Ruta `app/admin/page.tsx` (y sub-vistas) protegida en cliente.
- Componentes `components/admin/*`: layout con navegación, tablas y formularios.
- CRUD de cursos con campo `is_free` (requiere ajuste en schemas/endpoints admin).
- CRUD de módulos y lecciones (reutiliza endpoints existentes).
- Gestión de enrollments manuales (reutiliza endpoints existentes).
- Vista de leads/cotizaciones (consume endpoints de 002).
- Vista de métricas (consume endpoints de 006; la spec 006 define el formato).
- Funciones nuevas en `lib/api.ts` para los endpoints admin.
- Especificación SDD + casos TDD Vanilla.

### Excluye
- Los endpoints `/admin/leads*` y `/admin/metrics*` (los definen las specs 002 y 006; aquí solo se consumen).
- CRUD de apps de Labs (se añade como extensión en iteración posterior; el modelo ya existe por la spec 003).
- Gestión de usuarios/roles (solo lectura del propio admin; el rol `is_admin` ya existe).
- Diseño visual avanzado (se usa el sistema de componentes existente: `components/ui/button.tsx`, Tailwind).

## 4. Requisitos

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| R1 | `/admin` redirige a login si no hay token; muestra "acceso denegado" si el usuario no es admin | Alta |
| R2 | El layout del dashboard tiene navegación: Cursos, Enrollments, Leads, Métricas | Alta |
| R3 | Vista Cursos: listado con búsqueda, crear/editar/eliminar curso, incluyendo `is_free` (pago/gratuito) | Alta |
| R4 | Vista Curso: gestión de módulos (crear/editar/eliminar) | Alta |
| R5 | Vista Módulo: gestión de lecciones (crear/editar/eliminar, incluyendo `is_free` de lección y `video_key`) | Alta |
| R6 | Vista Enrollments: listar, otorgar y revocar inscripciones manuales | Alta |
| R7 | Vista Leads: listar leads con filtros, cambiar estado, asignar agente, crear cotización (spec 002) | Alta |
| R8 | Vista Métricas: mostrar métricas de acceso (spec 006) | Media |
| R9 | Los formularios validan en cliente y muestran errores del servidor (422/400) | Media |
| R10 | Las acciones destructivas (eliminar curso/módulo/lección, revocar enrollment) piden confirmación | Media |
| R11 | El backend admin soporta `is_free` en crear/editar curso (ajuste de schemas) | Alta |
| R12 | El formulario/endpoint admin de cursos rechaza `is_free=true` con `price_cents>0` (422) y expone el campo `is_free` | Alta |

## 5. Diseño / Arquitectura

### 5.1 Protección de la ruta (export estático)

Con `output: "export"` no hay protección server-side; la ruta `/admin` se protege en cliente:

1. Al montar `app/admin/page.tsx`, leer token de `localStorage` (patrón de `lib/api.ts`).
2. Sin token → redirigir a `/academy` (login) con mensaje.
3. Con token → `GET /auth/me`; si `user.is_admin !== true` → pantalla "Acceso denegado" (403).
4. La **seguridad real** la garantizan los endpoints del backend (todos los `/admin/*` exigen `require_admin`); la UI solo oculta la puerta.

### 5.2 Estructura de componentes

```
app/admin/page.tsx            → AdminDashboard (protección + layout + tabs)
components/admin/
  admin-layout.tsx            → barra lateral/tabs: Cursos | Enrollments | Leads | Métricas
  courses-table.tsx           → listado + búsqueda + acciones
  course-form.tsx             → crear/editar curso (name, slug, description, price_cents, is_free, is_active, image_path)
  modules-manager.tsx         → módulos del curso (crear/editar/eliminar)
  lessons-manager.tsx         → lecciones del módulo (title, is_free, video_key, duration_seconds, order)
  enrollments-panel.tsx       → listar/otorgar/revocar enrollments
  leads-panel.tsx             → lista de leads + detalle + cambio de estado + asignación + cotización
  metrics-panel.tsx           → métricas de acceso (spec 006)
```

### 5.3 Endpoints consumidos

**Existentes (reutilizar):**

| Endpoint | Uso |
|----------|-----|
| `POST /admin/courses` | Crear curso |
| `PATCH /admin/courses/{course_id}` | Editar curso |
| `DELETE /admin/courses/{course_id}` | Eliminar curso (409 si tiene enrollments — comportamiento ya implementado) |
| `POST /admin/courses/{course_id}/modules` | Crear módulo |
| `PATCH /admin/modules/{module_id}` | Editar módulo |
| `DELETE /admin/modules/{module_id}` | Eliminar módulo |
| `POST /admin/modules/{module_id}/lessons` | Crear lección |
| `PATCH /admin/lessons/{lesson_id}` | Editar lección |
| `DELETE /admin/lessons/{lesson_id}` | Eliminar lección |
| `GET /admin/enrollments` | Listar enrollments |
| `POST /admin/enrollments` | Otorgar enrollment manual (404 si el email no existe) |
| `DELETE /admin/enrollments` | Revocar enrollment (query params `email` + `course_id`, no `enrollment_id`) |

**Faltantes (especificar aquí o en 002/004/006):**

| Endpoint | Spec | Uso |
|----------|------|-----|
| `GET /admin/courses` (listado admin que **incluya** `is_active=false`; `GET /courses` público no sirve porque solo devuelve activos) | 005 | Listar cursos en el dashboard |
| `is_free` en `AdminCourseCreate`/`AdminCourseUpdate` (schemas) | 004/005 | Gestionar tipo pago/gratuito |
| `GET /admin/leads`, `GET /admin/leads/{id}`, `PATCH /admin/leads/{id}`, `POST /admin/leads/{id}/quote`, `GET /admin/leads/{id}/quote` | 002 | Vista Leads |
| `GET /admin/metrics`, `GET /admin/metrics/sections` | 006 | Vista Métricas |

**Nota (ya verificado en `backend/routers/admin.py`):** `GET /admin/courses` **no existe** — el router solo tiene POST/PATCH/DELETE de cursos. Hay que añadirlo en esta spec (listado admin con `is_active` incluido, a diferencia del público `GET /courses` que filtra `is_active=True`).

### 5.4 `lib/api.ts` — funciones nuevas

- `getAdminCourses()`, `createAdminCourse(payload)`, `updateAdminCourse(id, payload)`, `deleteAdminCourse(id)`.
- `createAdminModule(courseId, payload)`, `updateAdminModule(id, payload)`, `deleteAdminModule(id)`.
- `createAdminLesson(moduleId, payload)`, `updateAdminLesson(id, payload)`, `deleteAdminLesson(id)`.
- `getAdminEnrollments()`, `grantAdminEnrollment(payload)`, `revokeAdminEnrollment(payload)`.
- Funciones de leads (002): `getAdminLeads(filters)`, `getAdminLead(id)`, `patchAdminLead(id, payload)`, `createAdminQuote(leadId, payload)`.
- Funciones de métricas (006): `getAdminMetrics()`, `getAdminMetricsBySection()`.
- Todas envían `Authorization: Bearer <token>` (patrón existente).

### 5.5 Flujo de creación de curso con tipo pago/gratuito

```
Admin abre "Nuevo curso" → formulario con toggle "Gratuito" (is_free)
  ├─ is_free=true  → price_cents debe ser 0 (422 si > 0, regla de coherencia de 004); el curso se inscribe vía enroll-free (004)
  └─ is_free=false → price_cents obligatorio (> 0); se vende vía Stripe Checkout
POST /admin/courses {..., is_free, price_cents}
```

## 6. Criterios de aceptación

- [ ] `/admin` sin token redirige a login; con token de no-admin muestra "Acceso denegado".
- [ ] Un admin puede crear, editar y eliminar cursos, módulos y lecciones desde el navegador.
- [ ] El formulario de curso incluye el toggle pago/gratuito (`is_free`) y persiste correctamente.
- [ ] Un admin puede listar, otorgar y revocar enrollments manuales.
- [ ] La vista Leads permite filtrar, cambiar estado, asignar agente y crear cotización (endpoints de 002).
- [ ] La vista Métricas muestra los datos de 006.
- [ ] Las acciones destructivas piden confirmación.
- [ ] Los errores del servidor (400/422) se muestran en los formularios.

## 7. Riesgos y consideraciones

- **Seguridad en cliente:** la protección de `/admin` es solo UX; cualquier usuario puede inspeccionar el bundle. La autorización real está en los endpoints (ya protegidos). No agregar datos sensibles al bundle del frontend.
- **Export estático y rutas dinámicas:** con `output: "export"` no hay rutas dinámicas server-side; el dashboard será una SPA con tabs (no rutas `/admin/courses/{id}` separadas) o rutas estáticas con estado en cliente. Se recomienda SPA con tabs para simplicidad.
- **Dependencias:** la vista Leads requiere 002 implementada; la vista Métricas requiere 006. El dashboard puede entregarse por fases: primero Cursos/Enrollments (solo endpoints existentes + `is_free`), luego Leads y Métricas.
- **`is_free` en schemas admin:** tocar `AdminCourseCreate`/`AdminCourseUpdate` requiere actualizar también el seed y las pruebas existentes del backend (no romper el CRUD actual).
- **Confirmación de listado admin:** verificar si `GET /admin/courses` existe; si no, añadirlo (listado admin con `is_active` incluido, a diferencia del público).

## 8. Especificación funcional (SDD)

### 8.1 Protección de `/admin` (frontend)

- **Entrada:** montaje de `app/admin/page.tsx`.
- **Salida:** dashboard, redirección a login, o pantalla de acceso denegado.
- **Reglas:** sin token → redirigir a `/academy`; con token → `GET /auth/me`; `is_admin=false` → pantalla 403; `is_admin=true` → dashboard. Estado de verificación (spinner) mientras se valida.
- **Casos borde:** token expirado → redirigir a login (limpiar localStorage); backend caído → pantalla de error con reintento; recarga de página → re-validar siempre (no cachear el rol).

### 8.2 CRUD de cursos con `is_free` (backend + frontend)

- **Entrada:** formulario de curso (name, slug, description, price_cents, is_free, is_active, image_path).
- **Salida:** curso creado/actualizado/eliminado; tabla actualizada.
- **Reglas:** `is_free=true` → `price_cents` debe ser 0 (422 si > 0, regla de coherencia de 004 R11); `is_free=false` → `price_cents > 0` obligatorio (422 si no); slug/`id` único (el backend ya responde 400 con "ya existe" vía `create_course`); eliminar curso con enrollments → el backend **ya lo bloquea con 409 Conflict** (`delete_course` lanza `ValueError` → 409): la UI debe mostrar ese mensaje y no reintentar.
- **Casos borde:** id duplicado (400); precio 0 con `is_free=false`; editar un curso gratuito a pago con alumnos ya inscritos (los enrollments existentes se mantienen); eliminar curso inexistente → 404.

### 8.3 Gestión de enrollments manuales

- **Entrada:** email + course_id (otorgar); email + course_id (revocar — el endpoint `DELETE /admin/enrollments` toma **query params** `email` y `course_id`, no `enrollment_id`).
- **Salida:** enrollment creado/revocado; tabla actualizada.
- **Reglas:** otorgar usa `grant_enrollment_by_email` (idempotente; si el email no existe lanza `ValueError` → el router responde **404 "Usuario no encontrado"**, no crea el usuario — comportamiento actual verificado); revocar responde 404 si la inscripción no existe.
- **Casos borde:** otorgar dos veces el mismo enrollment → idempotente (check-then-insert existente; la robustez bajo concurrencia la cubre 007(g)); revocar enrollment inexistente → 404; curso inactivo → el enrollment se crea igual (decisión actual; si se quiere bloquear, es un ajuste futuro).

### 8.4 Vista Leads (consume 002)

- **Entrada:** filtros (estado, categoría, fechas), acciones (cambio de estado, asignación, cotización).
- **Salida:** tabla de leads + detalle + formulario de cotización.
- **Reglas:** solo admins (endpoints ya protegidos); al crear cotización, el lead pasa a `cotizado` (regla de 002); las transiciones inválidas muestran el error del servidor.
- **Casos borde:** lead sin cotización → botón "Crear cotización"; lead cotizado → "Editar cotización"; filtros sin resultados → tabla vacía con mensaje.

## 9. Casos de prueba (TDD Vanilla)

- `test_admin_route_redirects_to_login_without_token`: Arrange: sin token en localStorage. Act: montar `app/admin/page.tsx`. Assert: redirección a `/academy` (login).
- `test_admin_route_shows_denied_for_non_admin`: Arrange: token válido, `GET /auth/me` devuelve `is_admin=false`. Act: montar. Assert: pantalla "Acceso denegado", sin contenido del dashboard.
- `test_admin_route_shows_dashboard_for_admin`: Arrange: token válido, `is_admin=true`. Act: montar. Assert: dashboard con navegación (Cursos, Enrollments, Leads, Métricas).
- `test_admin_route_redirects_to_login_on_expired_token`: Arrange: `GET /auth/me` devuelve 401. Act: montar. Assert: redirección a login y token limpiado de localStorage.
- `test_course_form_requires_price_when_paid`: Arrange: formulario con `is_free=false`. Act: enviar con `price_cents=0`. Assert: error de validación en cliente, no se llama al endpoint.
- `test_course_form_ignores_price_when_free`: Arrange: formulario con `is_free=true`, `price_cents` vacío. Act: enviar. Assert: `POST /admin/courses` con `is_free=true` y sin error de precio.
- `test_course_form_rejects_free_with_positive_price`: Arrange: formulario con `is_free=true`, `price_cents=100`. Act: enviar. Assert: 422 (regla de coherencia de 004: `is_free=True` ⇒ `price_cents=0`), no se llama al endpoint.
- `test_course_form_shows_server_validation_errors`: Arrange: mock de `createAdminCourse` devolviendo 422 con detalle. Act: enviar. Assert: el detalle del servidor se muestra en el formulario.
- `test_courses_table_lists_and_searches`: Arrange: mock de listado con 3 cursos. Act: render y búsqueda por nombre. Assert: filas filtradas según el texto.
- `test_delete_course_requires_confirmation`: Arrange: curso con enrollments. Act: clic en eliminar. Assert: diálogo de confirmación; al confirmar, `deleteAdminCourse` invocado; si el backend responde 409 (tiene enrollments — comportamiento existente de `delete_course`), se muestra el error.
- `test_admin_courses_listing_includes_inactive`: Arrange: mock de `getAdminCourses` con 1 curso activo y 1 inactivo. Act: render tabla. Assert: ambos visibles con su estado (el endpoint nuevo `GET /admin/courses` no filtra por `is_active`).
- `test_enrollments_panel_grants_and_revokes`: Arrange: mocks de `grantAdminEnrollment` y `revokeAdminEnrollment`. Act: otorgar por email+curso y revocar por id. Assert: endpoints invocados con payload correcto y tabla refrescada.
- `test_leads_panel_lists_and_filters`: Arrange: mock de `getAdminLeads` con 2 leads. Act: render y filtro por estado. Assert: `getAdminLeads` invocado con el filtro y tabla actualizada.
- `test_leads_panel_creates_quote_and_moves_status`: Arrange: lead en `en_revision`, mock de `createAdminQuote`. Act: enviar cotización. Assert: endpoint invocado y la UI refleja el estado `cotizado`.
- `test_leads_panel_shows_invalid_transition_error`: Arrange: mock de `patchAdminLead` devolviendo 400 con detalle. Act: intentar transición inválida. Assert: mensaje del servidor visible.
- `test_metrics_panel_renders_section_data`: Arrange: mock de `getAdminMetricsBySection` con datos de 006. Act: render. Assert: se muestran las secciones con sus conteos.
- `test_admin_api_functions_send_bearer_token`: Arrange: mock de fetch. Act: llamar `getAdminCourses()`. Assert: header `Authorization: Bearer <token>` presente.

# 003 - Tonal-Tech Labs: listado de apps móviles, detalle, descarga y trailer

- **Estado:** aprobada (2026-10-01)
- **Fecha:** 2026-09-24
- **Autor:** Equipo Tonal-Tech

## 1. Resumen

La visión (FUNCIONALIDAD.md) define **Tonal-Tech Labs** como la sección donde se listan todos los desarrollos móviles de la empresa, con o sin precio; al seleccionar una app se abre su información completa, el link de descarga y un trailer desde YouTube. Hoy `labs` solo existe como categoría de servicio en `lib/tonal-data.ts` (su tarjeta en `ServiceGrid` abre el panel de leads vía `openLead(service.title)`), como enlace muerto en el header (`navLinks` → `href: '#servicios'`, un ancla, no `openLead`) y como texto plano en el footer (columna "Compañía", sin `href` real): **no hay listado, ni detalle, ni descarga, ni trailer** (gap Total, V5/V6 del spec 001).

Esta spec define el modelo de datos `App`, los endpoints públicos `GET /labs/apps` y `GET /labs/apps/{id}`, y los componentes frontend `LabsSection` + `AppDetailModal`, con la decisión justificada de alojar los datos en el **backend** (no estáticos).

## 2. Objetivos

- Crear la sección Labs con el listado de apps móviles (con o sin precio).
- Mostrar el detalle completo de cada app: descripción, capturas, precio, link de descarga y trailer de YouTube (embed).
- Servir los datos desde el backend para permitir gestión futura sin redeploy del frontend.
- Preparar la integración con métricas (spec 006) para medir visitas a Labs.
- Seguir el patrón existente de Academy (catálogo real vía `lib/api.ts`) en lugar del patrón estático de `lib/products.ts` (fuente de deuda, riesgo #2).

## 3. Alcance

### Incluye
- Modelo de datos `App` (backend) con seed inicial.
- Endpoints públicos `GET /labs/apps` y `GET /labs/apps/{id}`.
- Página `/labs` (frontend) con `LabsSection` (grid de tarjetas) y `AppDetailModal` (detalle, descarga, trailer).
- Embed de YouTube con modo de privacidad mejorada (`youtube-nocookie.com`).
- Enlace de Labs desde header/footer/landing hacia `/labs`.
- Especificación SDD + casos TDD Vanilla.

### Excluye
- Gestión CRUD de apps desde el dashboard admin (se añade en la spec 005 como extensión; aquí solo lectura pública).
- Pago/compra de apps dentro de Labs (la visión solo pide precio informativo y link de descarga).
- Subida de capturas/íconos (se referencian por URL; la gestión de archivos se define en 005).
- Analytics de visitas a detalle de app (lo cubre 006).

## 4. Requisitos

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| R1 | `GET /labs/apps` público devuelve solo apps activas, ordenadas por fecha de publicación desc | Alta |
| R2 | `GET /labs/apps/{id}` público devuelve el detalle completo de la app o 404 | Alta |
| R3 | El modelo `App` incluye precio opcional (`price_cents` nullable) para apps gratuitas o de pago | Alta |
| R4 | El detalle incluye link de descarga (`download_url`) y trailer de YouTube (`youtube_video_id`) | Alta |
| R5 | La página `/labs` lista las apps en tarjetas (ícono, nombre, categoría, precio o "Gratis") | Alta |
| R6 | Al seleccionar una app se abre `AppDetailModal` con info completa, botón de descarga y trailer embebido | Alta |
| R7 | Los datos viven en el backend (decisión justificada en 5.4), no en `lib/` estático | Alta |
| R8 | La página `/labs` maneja estados de carga, error y vacío | Media |
| R9 | El trailer se embebe con `youtube-nocookie.com` (privacidad) y `allowfullscreen` | Media |
| R10 | Header (`navLinks`, hoy ancla `#servicios`), footer (hoy texto plano) y la tarjeta Labs de `ServiceGrid` (hoy `openLead`) enlazan a `/labs` | Media |
| R11 | `GET /labs/apps` admite filtro opcional `?category=` con comparación case-sensitive; categoría sin resultados → lista vacía | Media |

## 5. Diseño / Arquitectura

### 5.1 Modelo de datos (backend/services/persistence.py)

**Tabla `apps`**

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | |
| `slug` | str unique | Identificador legible (ej. `tonal-inventory`) |
| `name` | str | Nombre de la app |
| `tagline` | str | Frase corta para la tarjeta |
| `description` | text | Descripción completa para el detalle |
| `category` | str | Ej. `logistica`, `educacion`, `salud` (libre) |
| `icon_url` | str | URL del ícono |
| `screenshots` | JSON | Lista de URLs de capturas (opcional) |
| `price_cents` | int nullable | `NULL` o `0` = gratuita; > 0 = de pago (precio informativo) |
| `currency` | str | Default `mxn` |
| `download_url` | str | Link de descarga (App Store / Google Play / APK) |
| `youtube_video_id` | str | ID del video de YouTube del trailer |
| `is_active` | bool | Default `True`; las inactivas no se listan |
| `published_at` | datetime | Orden del listado |
| `created_at` / `updated_at` | datetime | |

**Seed inicial:** 2–3 apps de ejemplo (una gratuita, una de pago) para desarrollo; el contenido real lo define el equipo.

### 5.2 Endpoints REST

| Método | Ruta | Autenticación | Descripción |
|--------|------|---------------|-------------|
| GET | `/labs/apps` | Pública | Lista `AppSummary` (id, slug, name, tagline, category, icon_url, price_cents, currency, is_free) de apps activas, orden `published_at` desc |
| GET | `/labs/apps/{app_id}` | Pública | Detalle `AppDetail` (todo lo anterior + description, screenshots, download_url, youtube_video_id) o 404 |

- Router nuevo `backend/routers/labs.py`, registrado en `backend/main.py`.
- `is_free` se deriva: `price_cents is None or price_cents == 0`.
- No se exponen campos internos (`is_active`, `created_at` internos) en la respuesta pública.

### 5.3 Frontend

- **Página:** `app/labs/page.tsx` (client component, patrón de `app/academy/page.tsx`).
- **`LabsSection`** (`components/labs/labs-section.tsx`): al montar, llama `getLabsApps()` (nueva función en `lib/api.ts`); renderiza grid de tarjetas; estados: cargando (spinner), error (mensaje + reintento), vacío ("Aún no hay apps publicadas").
- **`AppDetailModal`** (`components/labs/app-detail-modal.tsx`): recibe la app seleccionada (o la busca por id con `getLabsApp(id)`); muestra descripción, capturas, precio, botón "Descargar" (`download_url`, `target="_blank" rel="noopener noreferrer"`) y trailer embebido:
  ```html
  <iframe src="https://www.youtube-nocookie.com/embed/{youtube_video_id}"
          title="Trailer de {name}" allow="accelerometer; autoplay; clipboard-write;
          encrypted-media; gyroscope; picture-in-picture" allowfullscreen />
  ```
- **Navegación:** `components/site-header.tsx` (`navLinks`: cambiar `href: '#servicios'` por `href: '/labs'`), `components/site-footer.tsx` (columna "Compañía": convertir el texto plano 'Tonal-Tech Labs' en enlace real a `/labs`) y la tarjeta "Tonal-Tech Labs" de `lib/tonal-data.ts`/`ServiceGrid` (cambiar `openLead(service.title)` por un enlace `<Link href="/labs">`).
- **`lib/api.ts`:** añadir `getLabsApps(): Promise<AppSummary[]>` y `getLabsApp(id): Promise<AppDetail>` (sin JWT).

### 5.4 Decisión: datos en backend vs estáticos

**Decisión: backend.** Justificación:

1. **Gestión futura sin redeploy:** la visión contempla un dashboard admin (spec 005); con datos en backend, agregar/editar apps no requiere rebuild del frontend estático (GitHub Pages). Con datos estáticos, cada cambio exige commit + deploy.
2. **Consistencia con el patrón sano del proyecto:** Academy ya migró a catálogo real vía `lib/api.ts`; el catálogo estático `lib/products.ts` es precisamente el riesgo #2 (catálogos desincronizados). Repetir el patrón estático en Labs reintroduciría la misma deuda.
3. **Métricas (006):** el backend puede registrar vistas de detalle por app (`POST /metrics/page-view` con `section=labs`), lo que requiere que el backend conozca las apps.
4. **Costo:** el endpoint es de solo lectura y simple; el seed inicial cubre desarrollo. El costo de un router + tabla es bajo frente al beneficio.

**Contrapartida considerada:** los datos estáticos serían más rápidos de implementar y funcionarían sin backend en GitHub Pages. Se descarta porque Labs es contenido vivo de la empresa (nuevos desarrollos móviles), no contenido de marketing fijo.

## 6. Criterios de aceptación

- [ ] `GET /labs/apps` devuelve solo apps activas ordenadas por `published_at` desc.
- [ ] `GET /labs/apps/{id}` devuelve el detalle completo; 404 para id inexistente o app inactiva.
- [ ] Una app con `price_cents` nulo/0 se marca `is_free=true` en la respuesta.
- [ ] `/labs` lista las apps en tarjetas con estados de carga/error/vacío.
- [ ] Al hacer clic en una tarjeta se abre `AppDetailModal` con descripción, precio, botón de descarga y trailer de YouTube embebido.
- [ ] El enlace de Labs en header/footer/landing navega a `/labs` (ya no abre el panel de leads).
- [ ] No existe catálogo de apps duplicado en `lib/` (los datos viven solo en backend).

## 7. Riesgos y consideraciones

- **YouTube:** el embed depende de disponibilidad del video; si `youtube_video_id` es inválido, el iframe muestra error de YouTube (no rompe la página). Considerar validar el ID en seed.
- **`download_url`:** es un enlace externo; validar formato URL en el modelo (Pydantic `HttpUrl`) para evitar enlaces rotos.
- **Export estático:** `/labs` es client-rendered (igual que `/academy`); el contenido se carga en runtime desde el backend. Si el backend no está disponible, la página muestra el estado de error.
- **Precio informativo:** la visión no pide compra dentro de Labs; si en el futuro se quiere vender, se añadirá flujo de pago (fuera de alcance).
- **Dependencia con 005/006:** el CRUD de apps (005) y las métricas de Labs (006) consumen este modelo; mantener `slug` estable desde el inicio.

## 8. Especificación funcional (SDD)

### 8.1 `GET /labs/apps` (público)

- **Entrada:** ninguna (query opcional `category?` para filtrar; R11).
- **Salida:** 200 `{items: [AppSummary...]}`.

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

- **Reglas:** solo `is_active=True`; orden `published_at` desc; `is_free = price_cents is None or price_cents == 0`; no expone `is_active` ni timestamps internos; filtro `category` con comparación case-sensitive contra el valor de `category` del seed (categorías en minúsculas).
- **Casos borde:** sin apps activas → `items: []` (no error); filtro `category` sin resultados → lista vacía; categoría inexistente → lista vacía (no 400).

### 8.2 `GET /labs/apps/{app_id}` (público)

- **Entrada:** `app_id` (int).
- **Salida:** 200 `AppDetail` con todos los campos públicos.
- **Reglas:** app inexistente o `is_active=False` → 404 "App no encontrada".
- **Casos borde:** `app_id` no numérico → 422; app inactiva → 404 (no revela existencia); `screenshots` vacío → lista vacía en la respuesta.

### 8.3 `LabsSection` (frontend)

- **Entrada:** montaje de la página `/labs`.
- **Salida:** grid de tarjetas o estado de carga/error/vacío.
- **Reglas:** llama `getLabsApps()` al montar; clic en tarjeta → `onSelect(app)` abre el modal; botón de reintento en error.
- **Casos borde:** backend caído → mensaje de error con reintento; lista vacía → mensaje "Aún no hay apps publicadas"; doble clic rápido → no abre dos modales.

### 8.4 `AppDetailModal` (frontend)

- **Entrada:** app seleccionada (objeto completo).
- **Salida:** modal con info, botón de descarga y trailer.
- **Reglas:** botón "Descargar" abre `download_url` en pestaña nueva; iframe usa `youtube-nocookie.com/embed/{id}`; cierre con botón X, clic en backdrop o tecla Escape; el body no hace scroll mientras está abierto; gestión de foco: al abrir, el foco entra al modal (p. ej., botón de cierre); al cerrar, vuelve a la tarjeta que lo abrió.
- **Casos borde:** app sin `download_url` → ocultar botón (o mostrar "Próximamente"); `youtube_video_id` vacío → no renderizar iframe; Escape con foco en el iframe → el iframe captura la tecla (cerrar solo con botón/backdrop en ese caso).

## 9. Casos de prueba (TDD Vanilla)

- `test_list_apps_returns_only_active_ordered_by_published_at_desc`: Arrange: 3 apps (1 inactiva), fechas distintas. Act: `GET /labs/apps`. Assert: 2 apps, la más reciente primero, sin la inactiva.
- `test_list_apps_marks_free_when_price_null_or_zero`: Arrange: app con `price_cents=None` y app con `price_cents=0`. Act: `GET /labs/apps`. Assert: ambas con `is_free=True`.
- `test_list_apps_marks_paid_when_price_positive`: Arrange: app con `price_cents=9900`. Act: `GET /labs/apps`. Assert: `is_free=False`, `price_cents=9900`.
- `test_list_apps_returns_empty_when_no_active_apps`: Arrange: solo apps inactivas. Act: `GET /labs/apps`. Assert: 200 con `items: []`.
- `test_list_apps_filters_by_category`: Arrange: apps de 2 categorías. Act: `GET /labs/apps?category=logistica`. Assert: solo las de esa categoría.
- `test_list_apps_filters_by_category_no_results_returns_empty`: Arrange: apps de categoría `logistica`. Act: `GET /labs/apps?category=salud`. Assert: 200 con `items: []`.
- `test_get_app_detail_returns_full_info`: Arrange: app activa con screenshots, download_url y youtube_video_id. Act: `GET /labs/apps/{id}`. Assert: 200 con todos los campos.
- `test_get_app_detail_404_for_unknown_id`: Arrange: id inexistente. Act: `GET /labs/apps/99999`. Assert: 404.
- `test_get_app_detail_404_for_inactive_app`: Arrange: app con `is_active=False`. Act: `GET /labs/apps/{id}`. Assert: 404.
- `test_get_app_detail_rejects_non_numeric_id`: Arrange: `GET /labs/apps/abc`. Act: petición. Assert: 422.
- `test_labs_section_shows_loading_then_grid`: Arrange: mock de `getLabsApps` con promesa pendiente y luego resuelta con 2 apps. Act: montar `LabsSection`. Assert: primero spinner, luego 2 tarjetas.
- `test_labs_section_shows_error_with_retry`: Arrange: mock de `getLabsApps` rechazando. Act: montar. Assert: mensaje de error y botón de reintento que re-invoca la función.
- `test_labs_section_shows_empty_state`: Arrange: mock resolviendo `[]`. Act: montar. Assert: mensaje "Aún no hay apps publicadas".
- `test_app_detail_modal_renders_download_link_and_trailer`: Arrange: app con `download_url` y `youtube_video_id="abc123"`. Act: abrir modal. Assert: enlace de descarga con `target="_blank"` y iframe con `src` conteniendo `youtube-nocookie.com/embed/abc123`.
- `test_app_detail_modal_hides_download_when_missing`: Arrange: app sin `download_url`. Act: abrir modal. Assert: no se renderiza botón de descarga.
- `test_app_detail_modal_hides_trailer_when_no_video_id`: Arrange: app con `youtube_video_id=""`. Act: abrir modal. Assert: no se renderiza iframe.
- `test_app_detail_modal_closes_on_backdrop_and_escape`: Arrange: modal abierto. Act: clic en backdrop / tecla Escape. Assert: `onClose` invocado.
- `test_header_labs_link_navigates_to_labs_route`: Arrange: render de `SiteHeader`. Act: clic en "Tonal-Tech Labs". Assert: navega a `/labs` (hoy el enlace es un ancla muerta `#servicios`; no invoca `openLead`).

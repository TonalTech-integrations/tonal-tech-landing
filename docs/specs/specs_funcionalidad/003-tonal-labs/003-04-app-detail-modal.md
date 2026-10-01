# 003-04 - AppDetailModal (detalle, descarga y trailer)

- **Spec padre:** [003 - Tonal-Tech Labs: listado de apps móviles, detalle, descarga y trailer](../../003-tonal-labs.md) (secciones: 5.3, 8.4, 6, 7)
- **Estado:** borrador
- **Fecha:** 2026-09-28
- **Tipo:** Frontend
- **Dependencias:** 003-02 (el detalle de la app proviene de `GET /labs/apps/{id}` vía `getLabsApp(id)`); 003-03 (el modal se abre desde `LabsSection`)
- **Suite de pruebas sugerida:** Sugerida: `__tests__/labs/app-detail-modal.test.tsx`

## 1. Descripción

Modal `AppDetailModal` (`components/labs/app-detail-modal.tsx`) que muestra la información completa de la app seleccionada: descripción, capturas, precio, botón "Descargar" (`download_url`, `target="_blank" rel="noopener noreferrer"`) y trailer de YouTube embebido con modo de privacidad mejorada (`youtube-nocookie.com`).

## 2. Requisitos cubiertos

| ID padre | Requisito | Prioridad |
|----------|-----------|-----------|
| R6 | Al seleccionar una app se abre `AppDetailModal` con info completa, botón de descarga y trailer embebido | Alta |
| R9 | El trailer se embebe con `youtube-nocookie.com` (privacidad) y `allowfullscreen` | Media |

## 3. Diseño

**Frontend (5.3):**
- **`AppDetailModal`** (`components/labs/app-detail-modal.tsx`): recibe la app seleccionada (o la busca por id con `getLabsApp(id)`); muestra descripción, capturas, precio, botón "Descargar" (`download_url`, `target="_blank" rel="noopener noreferrer"`) y trailer embebido:

  ```html
  <iframe src="https://www.youtube-nocookie.com/embed/{youtube_video_id}"
          title="Trailer de {name}" allow="accelerometer; autoplay; clipboard-write;
          encrypted-media; gyroscope; picture-in-picture" allowfullscreen />
  ```

- **`lib/api.ts`:** añadir `getLabsApp(id): Promise<AppDetail>` (sin JWT).

## 4. Especificación funcional (SDD)

- **Entrada:** app seleccionada (objeto completo).
- **Salida:** modal con info, botón de descarga y trailer.
- **Reglas:** botón "Descargar" abre `download_url` en pestaña nueva (`target="_blank" rel="noopener noreferrer"`); iframe usa `youtube-nocookie.com/embed/{id}` con `allowfullscreen` (R9); cierre con botón X, clic en backdrop o tecla Escape; el body no hace scroll mientras está abierto.
- **Casos borde:** app sin `download_url` (null/vacío) → ocultar botón (o mostrar "Próximamente"); `youtube_video_id` vacío → no renderizar iframe; Escape con foco en el iframe → el iframe captura la tecla (cerrar solo con botón/backdrop en ese caso).
- **Gestión de foco (decisión confirmada, documentada en el padre 8.4):** al abrir, el foco entra al modal (p. ej., botón de cierre); al cerrar, vuelve a la tarjeta que lo abrió.

## 5. Criterios de aceptación

- [ ] Al hacer clic en una tarjeta se abre `AppDetailModal` con descripción, precio, botón de descarga y trailer de YouTube embebido.
- [ ] El trailer se embebe con `youtube-nocookie.com/embed/{id}` y `allowfullscreen` (R9).
- [ ] Si `download_url` es `null`/vacío, el botón de descarga no se renderiza.
- [ ] Si `youtube_video_id` es `null`/vacío, el iframe no se renderiza.
- [ ] El modal se cierra con botón X, clic en backdrop o tecla Escape; el body no hace scroll mientras está abierto.

## 6. Casos de prueba (TDD Vanilla)

- `test_app_detail_modal_renders_download_link_and_trailer`: Arrange: app con `download_url` y `youtube_video_id="abc123"`. Act: abrir modal. Assert: enlace de descarga con `target="_blank"` y iframe con `src` conteniendo `youtube-nocookie.com/embed/abc123`.
- `test_app_detail_modal_hides_download_when_missing`: Arrange: app sin `download_url`. Act: abrir modal. Assert: no se renderiza botón de descarga.
- `test_app_detail_modal_hides_trailer_when_no_video_id`: Arrange: app con `youtube_video_id=""`. Act: abrir modal. Assert: no se renderiza iframe.
- `test_app_detail_modal_closes_on_backdrop_and_escape`: Arrange: modal abierto. Act: clic en backdrop / tecla Escape. Assert: `onClose` invocado.
- `test_app_detail_modal_locks_body_scroll_while_open`: Arrange: modal abierto. Act: abrir. Assert: el body tiene scroll bloqueado (p. ej., `overflow: hidden`); al cerrar se restaura.
- `test_app_detail_modal_escape_with_iframe_focus_does_not_close`: Arrange: modal abierto con trailer. Act: foco dentro del iframe y tecla Escape. Assert: `onClose` NO invocado (el iframe captura la tecla; se cierra solo con botón/backdrop en ese caso).

## 7. Riesgos y consideraciones

- **YouTube:** el embed depende de disponibilidad del video; si `youtube_video_id` es inválido, el iframe muestra error de YouTube (no rompe la página). Considerar validar el ID en seed.

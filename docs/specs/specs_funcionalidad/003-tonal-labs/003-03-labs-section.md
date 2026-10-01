# 003-03 - Página /labs y LabsSection

- **Spec padre:** [003 - Tonal-Tech Labs: listado de apps móviles, detalle, descarga y trailer](../../003-tonal-labs.md) (secciones: 5.3, 8.3, 6, 7)
- **Estado:** borrador
- **Fecha:** 2026-09-28
- **Tipo:** Frontend
- **Dependencias:** 003-01 (los datos vienen de `GET /labs/apps` vía `getLabsApps()`)
- **Suite de pruebas sugerida:** Sugerida: `__tests__/labs/labs-section.test.tsx`

## 1. Descripción

Página `/labs` (client component, patrón de `app/academy/page.tsx`) con el componente `LabsSection` (`components/labs/labs-section.tsx`): al montar llama `getLabsApps()` (nueva función en `lib/api.ts`) y renderiza un grid de tarjetas (ícono, nombre, categoría, precio o "Gratis") con estados de carga (spinner), error (mensaje + reintento) y vacío ("Aún no hay apps publicadas").

## 2. Requisitos cubiertos

| ID padre | Requisito | Prioridad |
|----------|-----------|-----------|
| R5 | La página `/labs` lista las apps en tarjetas (ícono, nombre, categoría, precio o "Gratis") | Alta |
| R8 | La página `/labs` maneja estados de carga, error y vacío | Media |

## 3. Diseño

**Frontend (5.3):**
- **Página:** `app/labs/page.tsx` (client component, patrón de `app/academy/page.tsx`).
- **`LabsSection`** (`components/labs/labs-section.tsx`): al montar, llama `getLabsApps()` (nueva función en `lib/api.ts`); renderiza grid de tarjetas; estados: cargando (spinner), error (mensaje + reintento), vacío ("Aún no hay apps publicadas").
- **`lib/api.ts`:** añadir `getLabsApps(): Promise<AppSummary[]>` (sin JWT).

## 4. Especificación funcional (SDD)

- **Entrada:** montaje de la página `/labs`.
- **Salida:** grid de tarjetas o estado de carga/error/vacío.
- **Reglas:** llama `getLabsApps()` al montar; clic en tarjeta → `onSelect(app)` abre el modal; botón de reintento en error.
- **Casos borde:** backend caído → mensaje de error con reintento; lista vacía → mensaje "Aún no hay apps publicadas"; doble clic rápido → no abre dos modales.

## 5. Criterios de aceptación

- [ ] `/labs` muestra un spinner mientras `getLabsApps()` está pendiente y luego el grid de tarjetas.
- [ ] Si `getLabsApps()` falla, se muestra un mensaje de error con botón de reintento que re-invoca la función.
- [ ] Si `getLabsApps()` devuelve `[]`, se muestra "Aún no hay apps publicadas".
- [ ] El clic en una tarjeta invoca `onSelect(app)` (abre el modal); un doble clic rápido no abre dos modales.

## 6. Casos de prueba (TDD Vanilla)

- `test_labs_section_shows_loading_then_grid`: Arrange: mock de `getLabsApps` con promesa pendiente y luego resuelta con 2 apps. Act: montar `LabsSection`. Assert: primero spinner, luego 2 tarjetas.
- `test_labs_section_shows_error_with_retry`: Arrange: mock de `getLabsApps` rechazando. Act: montar. Assert: mensaje de error y botón de reintento que re-invoca la función.
- `test_labs_section_shows_empty_state`: Arrange: mock resolviendo `[]`. Act: montar. Assert: mensaje "Aún no hay apps publicadas".
- `test_labs_section_card_click_calls_on_select`: Arrange: mock de `getLabsApps` resuelto con 1 app. Act: clic en la tarjeta. Assert: `onSelect` invocado con la app.
- `test_labs_section_double_click_does_not_open_two_modals`: Arrange: mock de `getLabsApps` resuelto con 1 app. Act: doble clic rápido en la tarjeta. Assert: `onSelect` invocado una sola vez (no se abren dos modales).

## 7. Riesgos y consideraciones

- **Export estático:** `/labs` es client-rendered (igual que `/academy`); el contenido se carga en runtime desde el backend. Si el backend no está disponible, la página muestra el estado de error.

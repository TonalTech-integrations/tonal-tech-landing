# 003-05 - Navegación hacia /labs (header, footer, ServiceGrid)

- **Spec padre:** [003 - Tonal-Tech Labs: listado de apps móviles, detalle, descarga y trailer](../../003-tonal-labs.md) (secciones: 5.3, 6)
- **Estado:** borrador
- **Fecha:** 2026-09-28
- **Tipo:** Frontend
- **Dependencias:** 003-03 (la página `/labs` destino de los enlaces)
- **Suite de pruebas sugerida:** Sugerida: `__tests__/labs/navegacion-labs.test.tsx`

## 1. Descripción

Convierte los tres puntos de entrada actuales de Labs en enlaces reales a `/labs`: el header (`navLinks`, hoy ancla `#servicios`), el footer (columna "Compañía", hoy texto plano) y la tarjeta "Tonal-Tech Labs" de `lib/tonal-data.ts`/`ServiceGrid` (hoy `openLead(service.title)`).

## 2. Requisitos cubiertos

| ID padre | Requisito | Prioridad |
|----------|-----------|-----------|
| R10 | Header (`navLinks`, hoy ancla `#servicios`), footer (hoy texto plano) y la tarjeta Labs de `ServiceGrid` (hoy `openLead`) enlazan a `/labs` | Media |

## 3. Diseño

**Navegación (5.3):**
- `components/site-header.tsx` (`navLinks`): cambiar `href: '#servicios'` por `href: '/labs'`.
- `components/site-footer.tsx` (columna "Compañía"): convertir el texto plano 'Tonal-Tech Labs' en enlace real a `/labs`.
- Tarjeta "Tonal-Tech Labs" de `lib/tonal-data.ts`/`ServiceGrid`: cambiar `openLead(service.title)` por un enlace `<Link href="/labs">`.

## 4. Especificación funcional (SDD)

- **Entrada:** render de `SiteHeader`, `SiteFooter` y la tarjeta Labs de `ServiceGrid`.
- **Salida:** enlaces que navegan a `/labs` (ya no abren el panel de leads ni son anclas muertas).
- **Reglas:** `navLinks` apunta a `/labs`; el footer tiene enlace real a `/labs`; la tarjeta Labs usa `<Link href="/labs">` en lugar de `openLead`.
- **Casos borde:** los tres puntos de entrada (header, footer, ServiceGrid) navegan a `/labs`; el resto de `navLinks` (Academy, Casos de Éxito) y el resto de tarjetas de `ServiceGrid` conservan su comportamiento actual; la tarjeta Labs deja de invocar `openLead`, pero las demás tarjetas siguen abriendo el panel de leads.

## 5. Criterios de aceptación

- [ ] El enlace "Tonal-Tech Labs" del header (`navLinks`) navega a `/labs` (ya no es el ancla `#servicios`).
- [ ] El enlace "Tonal-Tech Labs" del footer (columna "Compañía") navega a `/labs` (ya no es texto plano sin `href`).
- [ ] La tarjeta "Tonal-Tech Labs" de `ServiceGrid` navega a `/labs` (ya no abre el panel de leads vía `openLead`).

## 6. Casos de prueba (TDD Vanilla)

- `test_header_labs_link_navigates_to_labs_route`: Arrange: render de `SiteHeader`. Act: clic en "Tonal-Tech Labs". Assert: navega a `/labs` (hoy el enlace es un ancla muerta `#servicios`; no invoca `openLead`).
- `test_footer_labs_link_navigates_to_labs_route`: Arrange: render de `SiteFooter`. Act: clic en "Tonal-Tech Labs" (columna "Compañía"). Assert: navega a `/labs` (hoy es un `<a href="#">` sin destino real).
- `test_service_grid_labs_card_navigates_to_labs_route`: Arrange: render de `ServiceGrid` (filtro Labs). Act: clic en la tarjeta "Tonal-Tech Labs". Assert: navega a `/labs` y NO invoca `openLead` (hoy abre el panel de leads).

## 7. Riesgos y consideraciones

- **Enlaces rotos:** si la ruta `/labs` cambia, los tres puntos quedan desincronizados; revisar los tres al renombrar la ruta.
- **Regresión en `ServiceGrid`:** al cambiar la tarjeta Labs de `openLead` a `<Link>`, verificar que las demás tarjetas siguen abriendo el panel de leads (el botón "Cotizar servicio" de cada tarjeta no se modifica).
- **Header móvil:** el menú móvil reutiliza el mismo array `navLinks`; el cambio aplica también al menú móvil (misma fuente).

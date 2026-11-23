# 002-08 - Mapeo del preset de servicio por id (bug título vs id)

- **Spec padre:** [002 - Sistema de leads y cotizaciones B2B](../../002-cotizacion-b2b.md) (secciones: 5.4, 8.1, 8.5)
- **Estado:** borrador
- **Fecha:** 2026-09-28
- **Tipo:** Frontend
- **Dependencias:** 002-07 (el mapeo se usa al abrir el panel vía `openLead(presetService)` dentro de la integración del `LeadProvider`)
- **Suite de pruebas sugerida:** Sugerida: `__tests__/leads/preset-service-mapping.test.tsx`

## 1. Descripción

Corrección del bug preexistente en el que los títulos de `services[]` no coinciden con `serviceCategoriesForm` (p. ej. `"Ciberseguridad Avanzada y Cumplimiento"` vs `"Ciberseguridad Avanzada"`), por lo que el pill preseleccionado no se activa. La implementación mapea por `id` estable del servicio (`optimizacion`/`cloud`/`ciberseguridad`/`soporte` → `optimizacion-comercial`/`arquitectura-cloud`/`ciberseguridad`/`soporte-computo`) y no por título.

## 2. Requisitos cubiertos

| ID padre | Requisito | Prioridad |
|----------|-----------|-----------|
| R9 | `LeadProvider` reemplaza `setTimeout` por llamada real a `POST /leads` con estados de UI (enviando / éxito / error) — parcial: el mapeo del preset es parte de la integración del `LeadProvider` (5.4) | Alta |

## 3. Diseño

**Mapeo (5.4):** el `presetService` que hoy recibe `openLead(service.title)` se mapea al `service_category` del backend por `id` estable del servicio (`services[]` de `lib/tonal-data.ts`):
- `optimizacion` → `optimizacion-comercial`
- `cloud` → `arquitectura-cloud`
- `ciberseguridad` → `ciberseguridad`
- `soporte` → `soporte-computo`
- `labs` → `labs` (tarjeta "Tonal-Tech Labs" del `ServiceGrid`)
- `academy` → `academy` (sin tarjeta en `services[]`; se elige solo por el pill `'Formación / Academy'` de `serviceCategoriesForm`)

Nunca por título (los títulos de `services[]` no coinciden con `serviceCategoriesForm`).

**Resolución del pill del formulario:** el pill se resuelve `id → service_category → etiqueta de serviceCategoriesForm`. Hoy `serviceCategoriesForm` son etiquetas de texto y el payload necesita el slug del backend; estructura recomendada sin cambiar el comportamiento visible: un mapa `serviceCategoryMap: {slug, label}` (p. ej. `{slug: "optimizacion-comercial", label: "Optimización Comercial y Analítica"}`) que alimenta tanto los pills como el payload (`service_category`).

## 4. Especificación funcional (SDD)

- **Entrada:** `openLead(presetService)` invocado desde la tarjeta de un servicio (p. ej. Ciberseguridad).
- **Salida:** el pill de `serviceCategoriesForm` correspondiente queda activo y el payload usa el `service_category` correcto.
- **Reglas:** el preset se resuelve por `id` de servicio (nunca por título) a una categoría válida (8.5).
- **Casos borde:** `service_category` con acentos o etiquetas de UI (el frontend mapea por `id` de servicio antes de enviar; el backend nunca recibe etiquetas de UI) (8.1).

## 5. Criterios de aceptación

- [ ] El preset se resuelve por `id` de servicio (nunca por título) para los 4 ids cotizables y `labs`; `academy` se elige solo por el pill.
- [ ] Un preset ausente o desconocido deja el formulario sin pill activo y sin error.

## 6. Casos de prueba (TDD Vanilla)

- `test_preset_service_maps_by_service_id_not_title`: Arrange: panel abierto vía `openLead` desde la tarjeta de Ciberseguridad. Act: inspeccionar el pill seleccionado. Assert: el pill de `serviceCategoriesForm` correspondiente queda activo (regresión del bug: `"Ciberseguridad Avanzada y Cumplimiento"` ≠ `"Ciberseguridad Avanzada"`).
- `test_preset_service_maps_all_quotable_ids_and_labs`: parametrizado sobre `optimizacion`, `cloud`, `ciberseguridad`, `soporte`, `labs`. Arrange: panel abierto vía `openLead` desde cada tarjeta. Act: inspeccionar el pill seleccionado y el payload. Assert: el pill de `serviceCategoriesForm` correspondiente queda activo y el payload usa el `service_category` correcto.
- `test_preset_service_unknown_or_absent_leaves_no_pill_active`: Arrange: `openLead` sin preset o con un id desconocido. Act: abrir el panel. Assert: ningún pill activo y sin error.

## 7. Riesgos y consideraciones

- **Regresión del bug por título:** cualquier llamada a `openLead` con un título (p. ej. `service.title`) en lugar del `id` reactiva el bug; el mapeo debe probarse por `id` (casos parametrizados de la sección 6).

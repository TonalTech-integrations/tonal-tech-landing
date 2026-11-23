# 002-07 - LeadProvider: envío real a POST /leads

- **Spec padre:** [002 - Sistema de leads y cotizaciones B2B](../../002-cotizacion-b2b.md) (secciones: 5.4, 8.5, 6)
- **Estado:** borrador
- **Fecha:** 2026-09-28
- **Tipo:** Frontend
- **Dependencias:** 002-01 (el endpoint `POST /leads` al que llama `createLead`); 002-08 (mapeo del preset por `id`); 002-09 (normalización de errores de `apiFetch`)
- **Suite de pruebas sugerida:** Sugerida: `__tests__/leads/lead-provider.test.tsx`

## 1. Descripción

Integración del `LeadProvider` existente (`components/lead-panel.tsx`) con el backend: reemplaza `window.setTimeout(() => setStage('done'), 2600)` por una llamada real a `POST /leads` vía `lib/api.ts` (nueva función `createLead(payload)`). Reutiliza el stage existente `diagnosing` (con su `DiagnosticTicker`) como estado de envío y agrega un nuevo stage `error`. Flujo: `form → diagnosing → done | error`.

## 2. Requisitos cubiertos

| ID padre | Requisito | Prioridad |
|----------|-----------|-----------|
| R9 | `LeadProvider` reemplaza `setTimeout` por llamada real a `POST /leads` con estados de UI (enviando / éxito / error) | Alta |

## 3. Diseño

**Integración (5.4):**
- Reemplazar `window.setTimeout(() => setStage('done'), 2600)` por una llamada a `POST /leads` vía `lib/api.ts` (nueva función `createLead(payload)`).
- Estados de UI: se reutiliza el stage existente `diagnosing` (con su `DiagnosticTicker`) como estado de envío; se agrega un nuevo stage `error`. Flujo: `form → diagnosing → done | error`.
- Payload enviado: `{service_category, contact_name: form.name, email: form.email, company_size: form.size, message: form.requirements}`.
- Validación de email: se mantiene la regex del cliente como UX inmediata, pero la validación **autoritativa** pasa al servidor (`EmailStr` de Pydantic → 422).
- `lib/api.ts` ya maneja JWT en localStorage; `POST /leads` no requiere token.

## 4. Especificación funcional (SDD)

- **Entrada:** `openLead(presetService?)` abre el panel; el formulario envía los datos.
- **Salida:** estados `form → diagnosing → done | error`.
- **Reglas:** al enviar, se llama `createLead` (POST /leads); en éxito → `done`; en error de red o 4xx → `error` con mensaje y botón de reintento; el panel no se cierra durante `diagnosing`; el preset se resuelve por `id` de servicio (nunca por título) a una categoría válida.
- **Stage `error` (5.4):** el usuario ve un mensaje de error (el `detail` normalizado por 002-09, p. ej. el 422 de validación) y un botón de reintento; los datos del formulario se conservan para reintentar sin reescribir; el panel permanece abierto. El reintento vuelve a `diagnosing` y reenvía el mismo payload.
- **Casos borde:** backend caído (error de red) → mensaje claro, sin pérdida de datos del formulario; 422 de validación → mostrar el mensaje normalizado del servidor; doble clic en enviar → deshabilitar botón durante `diagnosing`.

## 5. Criterios de aceptación

- [ ] El `LeadProvider` muestra `diagnosing` durante la llamada real y `done`/`error` según el resultado; ya no usa `setTimeout`.
- [ ] No queda ningún `setTimeout` en el flujo de envío (el único temporizador restante es el `setInterval` del `DiagnosticTicker`, que no controla la transición de estado).
- [ ] En `error` el usuario ve el mensaje normalizado (002-09) y un botón de reintento; los datos del formulario se conservan.

## 6. Casos de prueba (TDD Vanilla)

- `test_lead_provider_calls_real_endpoint_not_set_timeout`: Arrange: mock de `createLead` resolviendo. Act: enviar el formulario del panel. Assert: `createLead` invocado con el payload mapeado (`service_category` derivado del `id` del servicio, `company_size` incluido) y la UI pasa por `diagnosing` → `done`; no existe `setTimeout` en el flujo de envío.
- `test_lead_provider_shows_error_and_keeps_form_on_failure`: Arrange: mock de `createLead` rechazando. Act: enviar. Assert: estado `error`, mensaje visible, datos del formulario intactos, botón de reintento presente.
- `test_lead_provider_disables_submit_while_sending`: Arrange: mock de `createLead` con promesa pendiente. Act: enviar y hacer doble clic. Assert: el botón está deshabilitado y `createLead` se invoca una sola vez.
- `test_lead_provider_network_error_shows_error_stage`: Arrange: mock de `createLead` rechazando con error de red (fetch falla). Act: enviar. Assert: stage `error`, mensaje visible, botón de reintento, datos del formulario intactos.
- `test_lead_provider_422_shows_normalized_error_message`: Arrange: mock de `createLead` rechazando con el mensaje normalizado de 002-09 (p. ej. `"email: value is not a valid email address"`). Act: enviar. Assert: stage `error` y el mensaje normalizado visible.

## 7. Riesgos y consideraciones

- **Backend caído:** el error de red debe mostrar un mensaje claro sin perder los datos del formulario (8.5).
- **Validación autoritativa en servidor:** la regex del cliente es solo UX inmediata; el 422 del servidor (normalizado por 002-09) es la validación definitiva (5.4).

# 002-09 - Normalización de errores en apiFetch (detail 422 de Pydantic)

- **Spec padre:** [002 - Sistema de leads y cotizaciones B2B](../../002-cotizacion-b2b.md) (secciones: 5.4, 8.5)
- **Estado:** borrador
- **Fecha:** 2026-09-28
- **Tipo:** Frontend
- **Dependencias:** 002-07 (la normalización se usa en el flujo de envío del `LeadProvider` vía `createLead`)
- **Suite de pruebas sugerida:** Sugerida: `__tests__/api/api-fetch.test.ts`

## 1. Descripción

Ajuste necesario en `lib/api.ts`: `apiFetch` debe normalizar el `detail` de Pydantic (lista de objetos en 422) a un mensaje legible, porque hoy asume que `detail` es un string. Sin este ajuste, un 422 de `POST /leads` produciría un mensaje ilegible (`[object Object]`) en el stage `error` del `LeadProvider`.

## 2. Requisitos cubiertos

| ID padre | Requisito | Prioridad |
|----------|-----------|-----------|
| R9 | `LeadProvider` reemplaza `setTimeout` por llamada real a `POST /leads` con estados de UI (enviando / éxito / error) — parcial: la normalización de errores es parte del ajuste de `apiFetch` descrito en 5.4 | Alta |

## 3. Diseño

**Ajuste (5.4):** `lib/api.ts` ya maneja JWT en localStorage; `POST /leads` no requiere token. `apiFetch` debe normalizar el `detail` de Pydantic (lista de objetos en 422) a un mensaje legible, porque hoy asume que `detail` es un string.

## 4. Especificación funcional (SDD)

- **Entrada:** respuesta de fetch con 422 y `detail` como lista de errores Pydantic (objetos con `loc`/`msg`).
- **Salida:** `Error` lanzado con mensaje legible (no `[object Object]`).
- **Reglas:** `apiFetch` normaliza el `detail` de Pydantic (lista de objetos en 422) a un mensaje legible (5.4).
- **Algoritmo de normalización del `detail`:**
  1. Si `detail` es string → se usa tal cual.
  2. Si `detail` es lista de objetos Pydantic (`{loc, msg, type}`) → se toma cada `item.msg`, con el nombre de campo de `loc[-1]` como prefijo cuando exista (p. ej. `"email: value is not a valid email address"`), unidos por `"; "`.
  3. Si `detail` es objeto/otro tipo o falta → `"Error {status}"`.
- **Evidencia (lib/api.ts, ~96-103):** hoy `if (body?.detail) detail = body.detail` y luego `throw new Error(detail)`; con `detail` como lista produce `[object Object]`.
- **Casos borde:** 422 de validación → mostrar el mensaje normalizado del servidor (8.5).

## 5. Criterios de aceptación

- [ ] `apiFetch` normaliza el `detail` de Pydantic (lista de objetos en 422) a un mensaje legible; nunca lanza `[object Object]`.
- [ ] El comportamiento existente de limpiar el token ante 401 se mantiene.

## 6. Casos de prueba (TDD Vanilla)

- `test_api_fetch_normalizes_pydantic_422_detail`: Arrange: mock de fetch respondiendo 422 con `detail` como lista de errores Pydantic. Act: llamar `createLead`. Assert: el `Error` lanzado trae un mensaje legible (no `[object Object]`).
- `test_api_fetch_uses_string_detail_as_is`: Arrange: mock de fetch respondiendo 400 con `detail: "Categoría desconocida"`. Act: llamar `createLead`. Assert: el `Error` lanzado trae `"Categoría desconocida"`.
- `test_api_fetch_joins_multiple_pydantic_errors`: Arrange: mock de fetch respondiendo 422 con `detail` de 2 errores Pydantic (p. ej. `email` y `company_size`). Act: llamar `createLead`. Assert: mensaje con ambos `item.msg` con prefijo de campo, unidos por `"; "`.
- `test_api_fetch_falls_back_to_error_status_when_no_detail`: Arrange: mock de fetch respondiendo 500 sin `detail`. Act: llamar `createLead`. Assert: `Error("Error 500")`.
- `test_api_fetch_falls_back_when_body_not_json`: Arrange: mock de fetch respondiendo 502 con cuerpo no JSON. Act: llamar `createLead`. Assert: `Error("Error 502")`.
- `test_api_fetch_401_clears_token`: Arrange: token en localStorage, mock de fetch respondiendo 401. Act: llamar una función autenticada. Assert: `clearToken` invocado (comportamiento existente que no debe romperse).

## 7. Riesgos y consideraciones

- **Regresión en el manejo de 401:** la normalización no debe alterar la limpieza de token existente (`if (res.status === 401 && token) clearToken()` en `lib/api.ts`); se cubre con el caso de la sección 6.

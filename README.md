# Tonal Tech

Tonal Tech es una plataforma web con frontend en Next.js y backend en FastAPI. Está diseñada para ofrecer acceso a contenido de video protegido por pagos con Stripe y entrega de archivos mediante AWS S3.

## Características principales

- Frontend moderno con Next.js, Tailwind y componentes React.
- Backend con FastAPI para:
  - crear sesiones de pago de Stripe (`/payments/checkout-session`)
  - procesar webhooks de Stripe (`/payments/webhook`)
  - generar URLs pre-firmadas de AWS S3 para subida (`/videos/upload-url`)
  - generar URLs pre-firmadas de AWS S3 para descarga tras compra (`/videos/download-url`)
- Orquestación con Docker/Podman mediante `podman-compose.yml`.

## Estructura del proyecto

- `app/` - aplicación frontend de Next.js.
- `components/` - componentes UI reutilizables.
- `backend/` - servicio FastAPI, routers, servicios y configuración.
- `public/` - recursos públicos del frontend.
- `lib/` - utilidades y datos compartidos.

## Requisitos

- Node.js / pnpm para el frontend.
- Python 3.11+ para el backend.
- PostgreSQL si se usa persistencia local.
- Cuenta de Stripe y bucket de AWS S3 configurados.

## Configuración local

1. Clona el repositorio.
2. Crea las variables de entorno:
   - Copia `backend/.env.example` a `backend/.env`.
   - Copia `.env.local.example` a `.env.local` si usas variables del frontend.
3. Completa los valores de Stripe, AWS y `DATABASE_URL`.

### Variables importantes

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_ID`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `AWS_S3_BUCKET`
- `CORS_ORIGINS`
- `DATABASE_URL`
- `APP_URL`
- `NEXT_PUBLIC_API_BASE_URL`

## Ejecutar localmente

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

### Frontend

```bash
pnpm install
pnpm dev
```

El frontend se sirve en `http://localhost:3000` y el backend en `http://localhost:8000`.

## Ejecución con Docker / Podman

Si quieres usar la orquestación incluida:

```bash
podman-compose up --build
```

Este comando levanta los servicios:

- `frontend` en el puerto `3000`
- `backend` en el puerto `8000`

Asegúrate de definir las variables de entorno necesarias antes de arrancar.

## GitHub Pages

Para desplegar el frontend en GitHub Pages, usa exportación estática y despliega la carpeta `out`.

1. Define la ruta base si tu sitio no es `username.github.io`:

```bash
export NEXT_PUBLIC_BASE_PATH=/nombre-del-repositorio
```

2. Construye y exporta el sitio:

```bash
pnpm build:export
```

3. Publica el contenido de `out/` en GitHub Pages.

> Asegúrate de que el repositorio use la carpeta `out` como directorio de publicación y que el sitio deployado incluya `index.html` en la raíz.

También se agrega un archivo `.nojekyll` para evitar que GitHub Pages ignore carpetas y archivos especiales generados por Next.js.

## Endpoints útiles

- `GET /` - estado del backend.
- `POST /payments/checkout-session` - crea sesión de pago Stripe.
- `POST /payments/webhook` - recibe eventos de Stripe.
- `POST /videos/upload-url` - crea URL firmada para subir video.
- `GET /videos/download-url` - obtiene URL de descarga tras compra.

## Notas

- El backend usa CORS con orígenes permitidos definidos en `CORS_ORIGINS`.
- El frontend consume la API usando `NEXT_PUBLIC_API_BASE_URL`.
- El backend inicializa la base de datos en el evento `startup`.

## Licencia

Este repositorio no incluye una licencia explícita en la raíz. Añade una `LICENSE` si deseas aclarar los términos de uso.

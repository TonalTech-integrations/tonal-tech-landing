# Tonal Tech Backend

FastAPI backend for Tonal Tech with Stripe payment checkout, Stripe webhook processing, and AWS S3 video delivery.

## Install

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and update the values:

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_ID`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `AWS_S3_BUCKET`
- `CORS_ORIGINS`
- `DATABASE_URL` (PostgreSQL)
- `APP_URL`

## Database

Create a PostgreSQL database and set `DATABASE_URL` accordingly, for example:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/tonal_backend
```

## Run

```bash
cd backend
uvicorn backend.main:app --reload
```

Then open `http://127.0.0.1:8000/docs` to inspect the API.

## Features

- `POST /payments/checkout-session` to create Stripe Checkout sessions
- `POST /payments/webhook` to receive Stripe webhook events
- `GET /videos/download-url` to obtain a signed S3 video URL after purchase
- `POST /videos/upload-url` to generate a pre-signed S3 upload URL

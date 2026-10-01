from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.routers import admin, auth, courses, leads, payments, videos
from backend.services.persistence import init_db

settings = get_settings()

app = FastAPI(
    title="Tonal Tech Backend",
    description="FastAPI service for Stripe payments and AWS S3 video access.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    init_db()


app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(courses.lessons_router)
app.include_router(leads.router)
app.include_router(leads.admin_router)
app.include_router(payments.router)
app.include_router(videos.router)


@app.get("/")
def root() -> dict:
    return {"status": "ok", "service": "tonal-tech-backend"}

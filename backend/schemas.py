from datetime import date, datetime
from enum import Enum
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator


class CheckoutSessionRequest(BaseModel):
    course_id: str
    customer_email: Optional[EmailStr] = None


class CheckoutSessionResponse(BaseModel):
    session_id: str
    checkout_url: str


class WebhookEventResponse(BaseModel):
    received: bool
    type: str
    duplicate: Optional[bool] = None


class SignedUrlRequest(BaseModel):
    course_id: str
    customer_email: EmailStr


class SignedUrlResponse(BaseModel):
    download_url: str


class UploadUrlRequest(BaseModel):
    object_key: str = Field(min_length=1)
    content_type: Optional[str] = Field(default="video/mp4")


class UploadUrlResponse(BaseModel):
    upload_url: str
    object_key: str


class PurchaseStatus(str, Enum):
    pending = "pending"
    complete = "complete"
    failed = "failed"
    refunded = "refunded"


class PurchaseRecord(BaseModel):
    course_id: str
    customer_email: EmailStr
    stripe_session_id: str
    payment_status: PurchaseStatus
    video_key: str
    created_at: datetime
    updated_at: datetime


# ---------- Auth & Users ----------

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ---------- Courses catalog ----------

class LessonSummary(BaseModel):
    id: int
    title: str
    duration_min: int
    is_free: bool
    position: int
    has_access: bool = False
    stream_available: bool = False


class ModuleSummary(BaseModel):
    id: int
    title: str
    position: int
    lessons: list[LessonSummary]


class CourseSummary(BaseModel):
    id: str
    name: str
    tagline: str
    description: str
    price_cents: int
    currency: str
    level: str
    duration_hours: int
    image_path: str
    lessons_count: int
    enrolled: bool = False
    completed_lessons: int = 0


class CourseDetailResponse(CourseSummary):
    modules: list[ModuleSummary]


class CourseListResponse(BaseModel):
    courses: list[CourseSummary]


class MyCourseEntry(BaseModel):
    course_id: str
    name: str
    image_path: str
    total_lessons: int
    completed_lessons: int
    progress_pct: int


class MyCoursesResponse(BaseModel):
    courses: list[MyCourseEntry]


# ---------- Progress ----------

class LessonStatus(str, Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"


class LessonProgressUpdate(BaseModel):
    status: LessonStatus
    position_seconds: int = Field(default=0, ge=0)


class LessonProgressEntry(BaseModel):
    lesson_id: int
    status: LessonStatus
    position_seconds: int


class CourseProgressResponse(BaseModel):
    course_id: str
    lessons: list[LessonProgressEntry]


class StreamUrlResponse(BaseModel):
    stream_url: str
    expires_at: Optional[int] = None


# ---------- Admin ----------

class AdminCourseCreate(BaseModel):
    id: str = Field(..., min_length=2, pattern=r"^[a-z0-9-]+$")
    name: str
    tagline: str = ""
    description: str = ""
    price_cents: int = Field(default=0, ge=0)
    currency: str = "usd"
    level: str = ""
    duration_hours: int = Field(default=0, ge=0)
    image_path: str = ""


class AdminCourseUpdate(BaseModel):
    name: Optional[str] = None
    tagline: Optional[str] = None
    description: Optional[str] = None
    price_cents: Optional[int] = Field(default=None, ge=0)
    currency: Optional[str] = None
    level: Optional[str] = None
    duration_hours: Optional[int] = Field(default=None, ge=0)
    image_path: Optional[str] = None
    is_active: Optional[bool] = None


class AdminModuleCreate(BaseModel):
    title: str
    position: int = 0


class AdminModuleUpdate(BaseModel):
    title: Optional[str] = None
    position: Optional[int] = None


class AdminLessonCreate(BaseModel):
    title: str
    duration_min: int = Field(default=0, ge=0)
    video_key: str = ""
    is_free: bool = False
    position: int = 0


class AdminLessonUpdate(BaseModel):
    title: Optional[str] = None
    duration_min: Optional[int] = Field(default=None, ge=0)
    video_key: Optional[str] = None
    is_free: Optional[bool] = None
    position: Optional[int] = None


class AdminEnrollmentCreate(BaseModel):
    email: EmailStr
    course_id: str
    source: str = "manual"


class AdminEnrollmentEntry(BaseModel):
    enrollment_id: int
    user_email: str
    course_id: str
    source: str
    granted_at: datetime


class SessionStatusResponse(BaseModel):
    session_id: str
    status: str
    course_id: Optional[str] = None


# ---------- Leads y cotizaciones B2B (spec 002) ----------

# Las 4 secciones cotizables + labs/academy como consulta general.
SERVICE_CATEGORIES = (
    "optimizacion-comercial",
    "arquitectura-cloud",
    "ciberseguridad",
    "soporte-computo",
    "labs",
    "academy",
)

# Valores de companySizes del formulario (lib/tonal-data.ts).
COMPANY_SIZES = (
    "Mediana empresa",
    "Grande / Enterprise",
    "Profesional independiente",
)


class LeadCreate(BaseModel):
    service_category: str
    contact_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2)]
    email: EmailStr
    company_size: Literal[
        "Mediana empresa", "Grande / Enterprise", "Profesional independiente"
    ]
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5)]

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class LeadCreatedResponse(BaseModel):
    """Respuesta pública de POST /leads: no expone message ni assigned_agent_id (PII)."""

    id: int
    service_category: str
    contact_name: str
    email: str
    company_size: str
    status: str
    created_at: datetime


class LeadSummary(BaseModel):
    """Ítem del listado admin (002-02): sin `message` (solo va en el detalle, 002-03)."""

    id: int
    service_category: str
    contact_name: str
    email: str
    company_size: str
    status: str
    assigned_agent_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class LeadListResponse(BaseModel):
    items: list[LeadSummary]
    total: int
    page: int
    page_size: int


class LeadDetail(LeadSummary):
    """Detalle completo del lead (002-03): incluye `message` (solo admins)."""

    message: str


class QuoteResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    lead_id: int
    amount_cents: int
    currency: str
    valid_until: date
    notes: Optional[str] = None
    created_by: int
    created_at: datetime


class QuoteParamsResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    lead_id: int
    service_category: str
    params: dict
    version: int
    created_at: datetime


class LeadDetailResponse(BaseModel):
    lead: LeadDetail
    quote: Optional[QuoteResponse] = None
    quote_params: Optional[QuoteParamsResponse] = None

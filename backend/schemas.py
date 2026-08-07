from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class CourseId(str, Enum):
    codigo_limpio = "codigo_limpio"
    ciberseguridad = "ciberseguridad"
    negocios_digitales = "negocios_digitales"
    adopcion_corporativa = "adopcion_corporativa"


class CheckoutSessionRequest(BaseModel):
    course_id: CourseId
    customer_email: EmailStr


class CheckoutSessionResponse(BaseModel):
    session_id: str
    checkout_url: str


class WebhookEventResponse(BaseModel):
    received: bool
    type: str


class SignedUrlRequest(BaseModel):
    course_id: CourseId
    customer_email: EmailStr


class SignedUrlResponse(BaseModel):
    download_url: str


class UploadUrlRequest(BaseModel):
    object_key: str
    content_type: Optional[str] = Field(default="video/mp4")


class UploadUrlResponse(BaseModel):
    upload_url: str
    object_key: str


class PurchaseStatus(str, Enum):
    pending = "pending"
    complete = "complete"
    failed = "failed"


class PurchaseRecord(BaseModel):
    course_id: CourseId
    customer_email: EmailStr
    stripe_session_id: str
    payment_status: PurchaseStatus
    video_key: str
    created_at: datetime
    updated_at: datetime

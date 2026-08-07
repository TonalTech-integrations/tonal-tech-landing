from typing import Any

import stripe
from fastapi import HTTPException

from backend.config import get_settings
from backend.schemas import CourseId, PurchaseStatus
from backend.services.persistence import create_purchase_record, update_purchase_status

settings = get_settings()
stripe.api_key = settings.stripe_secret_key

COURSE_VIDEO_KEYS = {
    CourseId.codigo_limpio: "videos/codigo_limpio.mp4",
    CourseId.ciberseguridad: "videos/ciberseguridad.mp4",
    CourseId.negocios_digitales: "videos/negocios_digitales.mp4",
    CourseId.adopcion_corporativa: "videos/adopcion_corporativa.mp4",
}

PRICE_MAP = {
    CourseId.codigo_limpio: settings.stripe_price_id,
    CourseId.ciberseguridad: settings.stripe_price_id,
    CourseId.negocios_digitales: settings.stripe_price_id,
    CourseId.adopcion_corporativa: settings.stripe_price_id,
}


def create_checkout_session(course_id: CourseId, customer_email: str) -> stripe.checkout.Session:
    price_id = PRICE_MAP.get(course_id)
    if not price_id:
        raise HTTPException(status_code=400, detail="Course pricing configuration not found")

    session = stripe.checkout.Session.create(
        success_url=f"{settings.app_url}/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.app_url}/cancel",
        payment_method_types=["card"],
        mode="payment",
        customer_email=customer_email,
        line_items=[
            {
                "price": price_id,
                "quantity": 1,
            }
        ],
        metadata={
            "course_id": course_id.value,
        },
    )

    video_key = COURSE_VIDEO_KEYS[course_id]
    create_purchase_record(
        stripe_session_id=session.id,
        course_id=course_id,
        customer_email=customer_email,
        video_key=video_key,
    )

    return session


def construct_event(payload: bytes, sig_header: str) -> Any:
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.stripe_webhook_secret,
        )
        return event
    except stripe.error.SignatureVerificationError as error:
        raise HTTPException(status_code=400, detail=f"Webhook signature verification failed: {error}")


def handle_event(event: Any) -> dict:
    event_type = event["type"]

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session["id"]
        update_purchase_status(session_id, status=PurchaseStatus.complete)
        return {"received": True, "type": event_type}

    if event_type == "checkout.session.expired":
        session = event["data"]["object"]
        session_id = session["id"]
        update_purchase_status(session_id, status=PurchaseStatus.failed)
        return {"received": True, "type": event_type}

    return {"received": True, "type": event_type}

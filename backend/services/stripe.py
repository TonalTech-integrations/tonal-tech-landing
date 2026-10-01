import logging
from typing import Any

import stripe
from fastapi import HTTPException

from backend.config import get_settings
from backend.schemas import PurchaseStatus
from backend.services.persistence import (
    create_purchase_record,
    get_course,
    get_purchase_by_payment_intent,
    get_purchase_by_session,
    get_user_by_email,
    grant_enrollment_from_purchase,
    mark_event_processed,
    revoke_enrollment,
    set_purchase_payment_intent,
    update_purchase_status,
)

settings = get_settings()
stripe.api_key = settings.stripe_secret_key

logger = logging.getLogger(__name__)


def create_checkout_session(course_id: str, customer_email: str):
    """Crea la sesión de checkout usando el stripe_price_id del curso con fallback al global."""
    course = get_course(course_id)
    if not course or not course.is_active:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    if settings.payments_mock:
        return _create_mock_checkout_session(course, customer_email)

    price_id = course.stripe_price_id or settings.stripe_price_id
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
            "course_id": course_id,
        },
    )

    video_key = f"videos/{course_id}"
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

    if not mark_event_processed(event["id"], event_type):
        return {"received": True, "type": event_type, "duplicate": True}

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session["id"]
        update_purchase_status(session_id, status=PurchaseStatus.complete)
        payment_intent_id = session.get("payment_intent")
        if payment_intent_id:
            set_purchase_payment_intent(session_id, payment_intent_id)
        grant_enrollment_from_purchase(session_id)
        return {"received": True, "type": event_type}

    if event_type == "checkout.session.expired":
        session = event["data"]["object"]
        session_id = session["id"]
        update_purchase_status(session_id, status=PurchaseStatus.failed)
        return {"received": True, "type": event_type}

    if event_type == "charge.refunded":
        charge = event["data"]["object"]
        payment_intent_id = charge.get("payment_intent")
        purchase = get_purchase_by_payment_intent(payment_intent_id) if payment_intent_id else None
        if not purchase:
            logger.warning("Refund sin compra asociada: payment_intent=%s", payment_intent_id)
            return {"received": True, "type": event_type}
        update_purchase_status(purchase.stripe_session_id, status=PurchaseStatus.refunded)
        user = get_user_by_email(purchase.customer_email)
        if user:
            revoke_enrollment(user.id, purchase.course_id)
        return {"received": True, "type": event_type}

    if event_type == "checkout.session.async_payment_failed":
        session = event["data"]["object"]
        session_id = session["id"]
        update_purchase_status(session_id, status=PurchaseStatus.failed)
        purchase = get_purchase_by_session(session_id)
        if purchase:
            user = get_user_by_email(purchase.customer_email)
            if user:
                revoke_enrollment(user.id, purchase.course_id)
        return {"received": True, "type": event_type}

    return {"received": True, "type": event_type}


class _MockSession:
    """Imita stripe.checkout.Session para el modo simulado."""

    def __init__(self, session_id: str, url: str):
        self.id = session_id
        self.url = url


def _create_mock_checkout_session(course, customer_email: str) -> _MockSession:
    """Simula un pago exitoso sin llamar a Stripe: purchase complete + enrollment."""
    import uuid

    session_id = f"cs_mock_{uuid.uuid4().hex[:24]}"
    video_key = f"videos/{course.id}"
    create_purchase_record(
        stripe_session_id=session_id,
        course_id=course.id,
        customer_email=customer_email,
        video_key=video_key,
    )
    update_purchase_status(session_id, status=PurchaseStatus.complete)
    grant_enrollment_from_purchase(session_id)
    success_url = f"{settings.app_url}/success?session_id={session_id}"
    return _MockSession(session_id=session_id, url=success_url)

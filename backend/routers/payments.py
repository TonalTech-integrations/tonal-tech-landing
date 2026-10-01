from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.routers.auth import get_current_user_id
from backend.schemas import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    SessionStatusResponse,
    WebhookEventResponse,
)
from backend.services.persistence import get_purchase_by_session, get_user_by_id
from backend.services.stripe import construct_event, create_checkout_session, handle_event

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
def checkout_session(payload: CheckoutSessionRequest, user_id: int = Depends(get_current_user_id)):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    session = create_checkout_session(
        course_id=payload.course_id,
        customer_email=user.email,
    )
    return CheckoutSessionResponse(session_id=session.id, checkout_url=session.url)


@router.post("/webhook", response_model=WebhookEventResponse)
async def webhook(request: Request, stripe_signature: str | None = Header(None, alias="Stripe-Signature")):
    body = await request.body()
    if stripe_signature is None:
        return JSONResponse(status_code=400, content={"detail": "Stripe-Signature header is required"})

    event = construct_event(body, stripe_signature)
    result = handle_event(event)
    return result


@router.get("/session-status/{session_id}", response_model=SessionStatusResponse)
def session_status(session_id: str):
    purchase = get_purchase_by_session(session_id)
    if not purchase:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    course_id = str(purchase.course_id)
    status_value = (
        purchase.payment_status.value
        if hasattr(purchase.payment_status, "value")
        else str(purchase.payment_status)
    )
    return SessionStatusResponse(session_id=session_id, status=status_value, course_id=course_id)

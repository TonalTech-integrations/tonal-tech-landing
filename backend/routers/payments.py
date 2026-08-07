from fastapi import APIRouter, Body, Header, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.schemas import CheckoutSessionRequest, CheckoutSessionResponse, WebhookEventResponse
from backend.services.stripe import construct_event, create_checkout_session, handle_event

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
def checkout_session(payload: CheckoutSessionRequest):
    session = create_checkout_session(
        course_id=payload.course_id,
        customer_email=payload.customer_email,
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

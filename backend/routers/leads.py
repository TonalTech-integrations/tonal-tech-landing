from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.routers.admin import require_admin
from backend.schemas import (
    SERVICE_CATEGORIES,
    LeadCreate,
    LeadCreatedResponse,
    LeadDetail,
    LeadDetailResponse,
    LeadListResponse,
    LeadSummary,
    QuoteParamsResponse,
    QuoteResponse,
)
from backend.services.persistence import (
    create_lead,
    get_lead,
    get_lead_quote,
    get_lead_quote_params,
    list_leads,
)

router = APIRouter(tags=["leads"])
admin_router = APIRouter(prefix="/admin", tags=["leads"])


@router.post("/leads", response_model=LeadCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_lead_endpoint(payload: LeadCreate) -> LeadCreatedResponse:
    """Endpoint público (spec 002-01): persiste el lead con estado inicial `recibido`."""
    if payload.service_category not in SERVICE_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Categoría de servicio desconocida: {payload.service_category}",
        )
    lead = create_lead(
        service_category=payload.service_category,
        contact_name=payload.contact_name,
        email=str(payload.email).lower(),
        company_size=payload.company_size,
        message=payload.message,
    )
    return LeadCreatedResponse(
        id=lead.id,
        service_category=lead.service_category,
        contact_name=lead.contact_name,
        email=lead.email,
        company_size=lead.company_size,
        status=lead.status,
        created_at=lead.created_at,
    )


def _lead_summary(lead) -> LeadSummary:
    return LeadSummary(
        id=lead.id,
        service_category=lead.service_category,
        contact_name=lead.contact_name,
        email=lead.email,
        company_size=lead.company_size,
        status=lead.status,
        assigned_agent_id=lead.assigned_agent_id,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )


@admin_router.get("/leads", response_model=LeadListResponse)
def list_leads_endpoint(
    _: int = Depends(require_admin),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    service_category: Optional[str] = Query(default=None),
    date_from: Optional[date] = Query(default=None, alias="from"),
    date_to: Optional[date] = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> LeadListResponse:
    """Lista leads con filtros combinables, paginación y orden desc (002-02)."""
    items, total = list_leads(
        status_filter=status_filter,
        service_category=service_category,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return LeadListResponse(
        items=[_lead_summary(lead) for lead in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@admin_router.get("/leads/{lead_id}", response_model=LeadDetailResponse)
def get_lead_detail_endpoint(
    lead_id: int, _: int = Depends(require_admin)
) -> LeadDetailResponse:
    """Detalle del lead con su cotización y parámetros (002-03).

    `quote` es None si el lead no tiene cotización; `quote_params` es None solo si
    el lead no tiene fila (legado: desde 002-01 todo lead nace con su v1).
    """
    lead = get_lead(lead_id)
    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lead no encontrado"
        )
    quote = get_lead_quote(lead_id)
    quote_params = get_lead_quote_params(lead_id)
    summary = _lead_summary(lead)
    return LeadDetailResponse(
        lead=LeadDetail(**summary.model_dump(), message=lead.message),
        quote=QuoteResponse.model_validate(quote) if quote else None,
        quote_params=(
            QuoteParamsResponse.model_validate(quote_params) if quote_params else None
        ),
    )

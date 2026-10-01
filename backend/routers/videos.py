from fastapi import APIRouter, Depends, HTTPException, Query, Response

from backend.routers.admin import require_admin
from backend.routers.auth import get_current_user_id
from backend.schemas import SignedUrlResponse, UploadUrlRequest, UploadUrlResponse
from backend.services.persistence import get_completed_purchase, get_course, get_user_by_id, has_enrollment
from backend.services.storage import get_presigned_download_url, get_presigned_upload_url

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("/upload-url", response_model=UploadUrlResponse)
def upload_url(payload: UploadUrlRequest, _: int = Depends(require_admin)):
    upload_url = get_presigned_upload_url(
        object_key=payload.object_key,
        content_type=payload.content_type or "video/mp4",
    )
    return UploadUrlResponse(upload_url=upload_url, object_key=payload.object_key)


@router.get("/download-url", response_model=SignedUrlResponse, deprecated=True)
def download_url(
    response: Response,
    course_id: str = Query(..., description="Course ID for the requested video."),
    user_id: int = Depends(get_current_user_id),
):
    """Deprecado: usar /lessons/{id}/stream-url."""
    response.headers["Deprecation"] = "true"
    if not get_course(course_id):
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    user = get_user_by_id(user_id)
    if not user or not has_enrollment(user_id, course_id):
        raise HTTPException(status_code=403, detail="No tienes acceso a este curso.")

    purchase = get_completed_purchase(course_id=course_id, customer_email=user.email)
    video_key = purchase.video_key if purchase else f"videos/{course_id}"
    return SignedUrlResponse(download_url=get_presigned_download_url(object_key=video_key))

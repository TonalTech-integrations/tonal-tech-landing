from fastapi import APIRouter, HTTPException, Query

from backend.schemas import CourseId, SignedUrlResponse, UploadUrlRequest, UploadUrlResponse
from backend.services.persistence import get_completed_purchase
from backend.services.storage import get_presigned_download_url, get_presigned_upload_url

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("/upload-url", response_model=UploadUrlResponse)
def upload_url(payload: UploadUrlRequest):
    upload_url = get_presigned_upload_url(
        object_key=payload.object_key,
        content_type=payload.content_type or "video/mp4",
    )
    return UploadUrlResponse(upload_url=upload_url, object_key=payload.object_key)


@router.get("/download-url", response_model=SignedUrlResponse)
def download_url(
    course_id: CourseId = Query(..., description="Course ID for the requested video."),
    customer_email: str = Query(..., description="Customer email used for purchase verification."),
):
    purchase = get_completed_purchase(course_id=course_id, customer_email=customer_email)
    if not purchase:
        raise HTTPException(status_code=403, detail="No completed purchase found for this course and customer.")

    download_url = get_presigned_download_url(object_key=purchase.video_key)
    return SignedUrlResponse(download_url=download_url)

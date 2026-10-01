import time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.config import get_settings
from backend.routers.auth import get_current_user_id
from backend.schemas import (
    CourseDetailResponse,
    CourseListResponse,
    CourseProgressResponse,
    CourseSummary,
    LessonProgressEntry,
    LessonProgressUpdate,
    LessonSummary,
    ModuleSummary,
    StreamUrlResponse,
)
from backend.services.persistence import (
    count_completed_lessons,
    count_course_lessons,
    get_course,
    get_course_modules,
    get_course_progress,
    get_enrolled_course_ids,
    get_lesson,
    get_module_lessons,
    has_enrollment,
    list_active_courses,
    upsert_lesson_progress,
    user_has_lesson_access,
)
from backend.services.storage import get_presigned_download_url

router = APIRouter(prefix="/courses", tags=["courses"])
lessons_router = APIRouter(prefix="/lessons", tags=["lessons"])

security = HTTPBearer(auto_error=False)
settings = get_settings()
STREAM_URL_TTL_SECONDS = 900


def _optional_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int | None:
    if credentials is None:
        return None
    try:
        return get_current_user_id(credentials)
    except HTTPException:
        return None


def _course_summary(course, user_id: int | None) -> CourseSummary:
    total = count_course_lessons(course.id)
    enrolled = user_id is not None and has_enrollment(user_id, course.id)
    completed = count_completed_lessons(user_id, course.id) if enrolled else 0
    return CourseSummary(
        id=course.id,
        name=course.name,
        tagline=course.tagline,
        description=course.description,
        price_cents=course.price_cents,
        currency=course.currency,
        level=course.level,
        duration_hours=course.duration_hours,
        image_path=course.image_path,
        lessons_count=total,
        enrolled=enrolled,
        completed_lessons=completed,
    )


@router.get("", response_model=CourseListResponse)
def list_courses(user_id: int | None = Depends(_optional_user_id)):
    courses = [_course_summary(c, user_id) for c in list_active_courses()]
    return CourseListResponse(courses=courses)


@router.get("/{course_id}", response_model=CourseDetailResponse)
def course_detail(course_id: str, user_id: int | None = Depends(_optional_user_id)):
    course = get_course(course_id)
    if not course or not course.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado")

    summary = _course_summary(course, user_id)
    modules = []
    for module in get_course_modules(course.id):
        lessons = []
        for lesson in get_module_lessons(module.id):
            has_access = lesson.is_free or (user_id is not None and has_enrollment(user_id, course.id))
            lessons.append(
                LessonSummary(
                    id=lesson.id,
                    title=lesson.title,
                    duration_min=lesson.duration_min,
                    is_free=lesson.is_free,
                    position=lesson.position,
                    has_access=has_access,
                    stream_available=has_access and bool(lesson.video_key),
                )
            )
        modules.append(
            ModuleSummary(id=module.id, title=module.title, position=module.position, lessons=lessons)
        )

    return CourseDetailResponse(**summary.model_dump(), modules=modules)


@router.get("/{course_id}/progress", response_model=CourseProgressResponse)
def course_progress(course_id: str, user_id: int = Depends(get_current_user_id)):
    course = get_course(course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado")
    if not has_enrollment(user_id, course_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No tienes acceso a este curso"
        )
    entries = [
        LessonProgressEntry(
            lesson_id=p.lesson_id, status=p.status, position_seconds=p.position_seconds
        )
        for p in get_course_progress(user_id, course_id)
    ]
    return CourseProgressResponse(course_id=course_id, lessons=entries)


@lessons_router.put("/{lesson_id}/progress", response_model=LessonProgressEntry)
def update_lesson_progress(
    lesson_id: int,
    payload: LessonProgressUpdate,
    user_id: int = Depends(get_current_user_id),
):
    if not user_has_lesson_access(user_id, lesson_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No tienes acceso a esta lección"
        )
    progress = upsert_lesson_progress(user_id, lesson_id, payload.status, payload.position_seconds)
    return LessonProgressEntry(
        lesson_id=progress.lesson_id,
        status=progress.status,
        position_seconds=progress.position_seconds,
    )


@lessons_router.get("/{lesson_id}/stream-url", response_model=StreamUrlResponse)
def lesson_stream_url(lesson_id: int, user_id: int = Depends(get_current_user_id)):
    lesson = get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lección no encontrada")
    if not user_has_lesson_access(user_id, lesson_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No tienes acceso a esta lección"
        )
    if not lesson.video_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Esta lección no tiene video disponible"
        )
    url = get_presigned_download_url(object_key=lesson.video_key, expires_in=STREAM_URL_TTL_SECONDS)
    return StreamUrlResponse(stream_url=url, expires_at=int(time.time()) + STREAM_URL_TTL_SECONDS)

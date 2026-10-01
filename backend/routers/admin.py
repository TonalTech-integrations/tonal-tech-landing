from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from backend.routers.auth import get_current_user_id
from backend.schemas import (
    AdminCourseCreate,
    AdminCourseUpdate,
    AdminEnrollmentCreate,
    AdminEnrollmentEntry,
    AdminLessonCreate,
    AdminLessonUpdate,
    AdminModuleCreate,
    AdminModuleUpdate,
)
from backend.services import persistence as db

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(user_id: int = Depends(get_current_user_id)) -> int:
    user = db.get_user_by_id(user_id)
    if not user or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador",
        )
    return user_id


# ---------- Cursos ----------


@router.post("/courses", status_code=status.HTTP_201_CREATED)
def create_course(payload: AdminCourseCreate, _: int = Depends(require_admin)):
    data = payload.model_dump()
    data["course_id"] = data.pop("id")
    try:
        course = db.create_course(**data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"id": course.id, "name": course.name}


@router.patch("/courses/{course_id}")
def update_course(
    course_id: str, payload: AdminCourseUpdate, _: int = Depends(require_admin)
):
    course = db.update_course(course_id, **payload.model_dump(exclude_unset=True))
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado")
    return {"id": course.id, "is_active": course.is_active}


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: str, _: int = Depends(require_admin)):
    try:
        deleted = db.delete_course(course_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado")


# ---------- Módulos ----------


@router.post("/courses/{course_id}/modules", status_code=status.HTTP_201_CREATED)
def create_module(
    course_id: str, payload: AdminModuleCreate, _: int = Depends(require_admin)
):
    try:
        module = db.create_module(course_id, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return {"id": module.id, "title": module.title, "position": module.position}


@router.patch("/modules/{module_id}")
def update_module(
    module_id: int, payload: AdminModuleUpdate, _: int = Depends(require_admin)
):
    module = db.update_module(module_id, **payload.model_dump(exclude_unset=True))
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Módulo no encontrado")
    return {"id": module.id, "title": module.title, "position": module.position}


@router.delete("/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_module(module_id: int, _: int = Depends(require_admin)):
    if not db.delete_module(module_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Módulo no encontrado")


# ---------- Lecciones ----------


@router.post("/modules/{module_id}/lessons", status_code=status.HTTP_201_CREATED)
def create_lesson(
    module_id: int, payload: AdminLessonCreate, _: int = Depends(require_admin)
):
    try:
        lesson = db.create_lesson(module_id, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return {"id": lesson.id, "title": lesson.title, "video_key": lesson.video_key}


@router.patch("/lessons/{lesson_id}")
def update_lesson(
    lesson_id: int, payload: AdminLessonUpdate, _: int = Depends(require_admin)
):
    lesson = db.update_lesson(lesson_id, **payload.model_dump(exclude_unset=True))
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lección no encontrada")
    return {"id": lesson.id, "title": lesson.title, "video_key": lesson.video_key}


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson(lesson_id: int, _: int = Depends(require_admin)):
    if not db.delete_lesson(lesson_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lección no encontrada")


# ---------- Enrollments manuales ----------


@router.get("/enrollments", response_model=List[AdminEnrollmentEntry])
def list_enrollments(_: int = Depends(require_admin)):
    return db.list_enrollments()


@router.post("/enrollments", status_code=status.HTTP_201_CREATED)
def grant_enrollment(payload: AdminEnrollmentCreate, _: int = Depends(require_admin)):
    try:
        db.grant_enrollment_by_email(payload.email, payload.course_id, payload.source)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return {"granted": True, "email": payload.email, "course_id": payload.course_id}


@router.delete("/enrollments", status_code=status.HTTP_204_NO_CONTENT)
def revoke_enrollment(
    email: str, course_id: str, _: int = Depends(require_admin)
):
    if not db.revoke_enrollment_by_email(email, course_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inscripción no encontrada"
        )

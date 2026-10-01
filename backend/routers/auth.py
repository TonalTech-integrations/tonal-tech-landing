from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from backend.config import get_settings
from backend.schemas import (
    MyCourseEntry,
    MyCoursesResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from backend.services.persistence import (
    count_completed_lessons,
    count_course_lessons,
    create_user,
    get_course,
    get_enrolled_course_ids,
    get_user_by_email,
    get_user_by_id,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()
settings = get_settings()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
            )
        return int(user_id)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado"
        )


def _token_response(user) -> TokenResponse:
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user=UserResponse(id=user.id, email=user.email, created_at=user.created_at),
    )


@router.post("/register", response_model=TokenResponse)
def register(payload: UserRegisterRequest):
    if get_user_by_email(payload.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="El email ya está registrado"
        )
    user = create_user(email=payload.email, hashed_password=hash_password(payload.password))
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLoginRequest):
    user = get_user_by_email(payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )
    return _token_response(user)


@router.get("/me", response_model=UserResponse)
def get_me(user_id: int = Depends(get_current_user_id)):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado"
        )
    return UserResponse(id=user.id, email=user.email, created_at=user.created_at)


@router.get("/users/me/courses", response_model=MyCoursesResponse)
def get_my_courses(user_id: int = Depends(get_current_user_id)):
    entries = []
    for course_id in get_enrolled_course_ids(user_id):
        course = get_course(course_id)
        if not course:
            continue
        total = count_course_lessons(course_id)
        completed = count_completed_lessons(user_id, course_id)
        entries.append(
            MyCourseEntry(
                course_id=course.id,
                name=course.name,
                image_path=course.image_path,
                total_lessons=total,
                completed_lessons=completed,
                progress_pct=round(completed * 100 / total) if total else 0,
            )
        )
    return MyCoursesResponse(courses=entries)

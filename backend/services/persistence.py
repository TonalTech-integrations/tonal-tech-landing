import os
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

import bcrypt
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    func,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.config import get_settings
from backend.schemas import LessonStatus, PurchaseStatus

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = get_settings().database_url
CONNECT_ARGS = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=CONNECT_ARGS)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Course(Base):
    __tablename__ = "courses"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    tagline = Column(String, nullable=False, default="")
    description = Column(String, nullable=False, default="")
    price_cents = Column(Integer, nullable=False, default=0)
    currency = Column(String, nullable=False, default="usd")
    level = Column(String, nullable=False, default="")
    duration_hours = Column(Integer, nullable=False, default=0)
    image_path = Column(String, nullable=False, default="")
    is_active = Column(Boolean, nullable=False, default=True)
    stripe_price_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CourseModule(Base):
    __tablename__ = "course_modules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    position = Column(Integer, nullable=False, default=0)


class CourseLesson(Base):
    __tablename__ = "course_lessons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    module_id = Column(Integer, ForeignKey("course_modules.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    duration_min = Column(Integer, nullable=False, default=0)
    video_key = Column(String, nullable=False, default="")
    is_free = Column(Boolean, nullable=False, default=False)
    position = Column(Integer, nullable=False, default=0)


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_enrollment_user_course"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False, index=True)
    source = Column(String, nullable=False, default="purchase")
    granted_at = Column(DateTime, default=datetime.utcnow)


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_progress_user_lesson"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    lesson_id = Column(Integer, ForeignKey("course_lessons.id"), nullable=False, index=True)
    status = Column(SqlEnum(LessonStatus), nullable=False, default=LessonStatus.not_started)
    position_seconds = Column(Integer, nullable=False, default=0)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Purchase(Base):
    __tablename__ = "purchases"

    stripe_session_id = Column(String, primary_key=True, index=True)
    course_id = Column(String, nullable=False)
    customer_email = Column(String, nullable=False, index=True)
    payment_status = Column(SqlEnum(PurchaseStatus), nullable=False, default=PurchaseStatus.pending)
    payment_intent_id = Column(String, nullable=True)
    video_key = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProcessedWebhookEvent(Base):
    __tablename__ = "processed_webhook_events"

    event_id = Column(String, primary_key=True)
    type = Column(String, nullable=True)
    processed_at = Column(DateTime, default=datetime.utcnow)


# ---------- Leads y cotizaciones B2B (spec 002) ----------

# Estados del lead: recibido -> en_revision -> cotizado -> cerrado (5.5 de la spec).
# Se almacena como String (no enum nativo) para poder añadir estados sin migraciones
# ALTER TYPE en PostgreSQL (lección aprendida de purchasestatus); las transiciones
# válidas se validan a nivel de aplicación en el PATCH (002-04).
LEAD_STATUS_RECIBIDO = "recibido"


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_category = Column(String, nullable=False, index=True)
    contact_name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    company_size = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String, nullable=False, default=LEAD_STATUS_RECIBIDO, index=True)
    assigned_agent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class QuoteParams(Base):
    __tablename__ = "quote_params"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    service_category = Column(String, nullable=False)
    params = Column(JSON, nullable=False, default=dict)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class Quote(Base):
    """Una cotización activa por lead (002-05 la crea/actualiza; 002-03 la expone)."""

    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(
        Integer, ForeignKey("leads.id"), nullable=False, unique=True, index=True
    )
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String, nullable=False, default="mxn")
    valid_until = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


COURSE_SEED = [
    {
        "id": "plc-industrial",
        "name": "Automatización con PLC",
        "tagline": "Programación de controladores lógicos desde cero hasta procesos industriales.",
        "description": "Domina la programación de PLCs con ladder logic, instrumentación de campo y despliegue en planta.",
        "price_cents": 14900,
        "level": "Intermedio",
        "duration_hours": 12,
        "image_path": "/courses/plc-industrial.png",
        "modules": [
            {
                "title": "Fundamentos de control industrial",
                "lessons": [
                    {"title": "Arquitectura de un PLC y ciclo de scan", "duration_min": 22, "free": True},
                    {"title": "Ladder logic: contactos, bobinas y timers", "duration_min": 34},
                    {"title": "Entradas y salidas: cableado y diagnóstico", "duration_min": 28},
                ],
            },
            {
                "title": "Programación avanzada",
                "lessons": [
                    {"title": "PID y control de procesos continuos", "duration_min": 41},
                    {"title": "Comunicación Modbus TCP/RTU", "duration_min": 37},
                    {"title": "Proyecto: línea de embotellado completa", "duration_min": 58},
                ],
            },
        ],
    },
    {
        "id": "scada-redes",
        "name": "SCADA y Redes Industriales",
        "tagline": "Diseña sistemas de supervisión y redes OT seguras y escalables.",
        "description": "Arquitectura SCADA, protocolos industriales y segmentación de redes OT con criterios de ciberseguridad.",
        "price_cents": 18900,
        "level": "Avanzado",
        "duration_hours": 15,
        "image_path": "/courses/scada-networks.png",
        "modules": [
            {
                "title": "Arquitectura SCADA",
                "lessons": [
                    {"title": "Componentes: RTU, HMI, historiadores", "duration_min": 26, "free": True},
                    {"title": "OPC UA e integración de datos", "duration_min": 33},
                ],
            },
            {
                "title": "Redes OT y seguridad",
                "lessons": [
                    {"title": "Modelo Purdue y segmentación", "duration_min": 31},
                    {"title": "Monitoreo y detección de anomalías", "duration_min": 44},
                    {"title": "Proyecto: SCADA para planta de tratamiento", "duration_min": 62},
                ],
            },
        ],
    },
    {
        "id": "robotica-industrial",
        "name": "Robótica Industrial",
        "tagline": "Programación de brazos robóticos y celdas de trabajo colaborativas.",
        "description": "Cinemática, trayectorias y puesta en marcha de robots industriales con casos reales de manufactura.",
        "price_cents": 12900,
        "level": "Básico",
        "duration_hours": 9,
        "image_path": "/courses/robotics.png",
        "modules": [
            {
                "title": "Introducción a la robótica",
                "lessons": [
                    {"title": "Tipos de robots y grados de libertad", "duration_min": 19, "free": True},
                    {"title": "Frames, TCP y sistemas de coordenadas", "duration_min": 27},
                ],
            },
            {
                "title": "Programación de trayectorias",
                "lessons": [
                    {"title": "Movimientos joint, lineales y circulares", "duration_min": 35},
                    {"title": "Proyecto: celda de pick and place", "duration_min": 52},
                ],
            },
        ],
    },
]


def init_db() -> None:
    if DATABASE_URL.startswith("sqlite"):
        data_dir = BASE_DIR / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _ensure_column(
        "users",
        "is_admin",
        "ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE",
    )
    _ensure_column(
        "courses",
        "stripe_price_id",
        "ALTER TABLE courses ADD COLUMN stripe_price_id VARCHAR",
    )
    _ensure_column(
        "purchases",
        "payment_intent_id",
        "ALTER TABLE purchases ADD COLUMN payment_intent_id VARCHAR",
    )
    _ensure_purchase_status_refunded()
    _migrate_purchase_course_id_to_string()
    seed_courses()


def _ensure_column(table: str, column: str, ddl: str) -> None:
    """ALTER TABLE suave para bases ya existentes (sin Alembic)."""
    from sqlalchemy import inspect, text

    existing = {c["name"] for c in inspect(engine).get_columns(table)}
    if column in existing:
        return
    with engine.begin() as conn:
        conn.execute(text(ddl))


def _ensure_purchase_status_refunded() -> None:
    """Añade el valor 'refunded' al enum de payment_status en PostgreSQL (autocommit)."""
    if engine.dialect.name != "postgresql":
        return
    from sqlalchemy import inspect, text

    columns = {c["name"]: c["type"] for c in inspect(engine).get_columns("purchases")}
    enum_type = columns.get("payment_status")
    type_name = getattr(enum_type, "name", None) or "purchasestatus"
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(f"ALTER TYPE {type_name} ADD VALUE IF NOT EXISTS 'refunded'"))


def _migrate_purchase_course_id_to_string() -> None:
    """Recrea purchases.course_id como VARCHAR si aún es enum, preservando filas."""
    from sqlalchemy import inspect, text

    columns = {c["name"]: c["type"] for c in inspect(engine).get_columns("purchases")}
    if not isinstance(columns.get("course_id"), SqlEnum):
        return
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE purchases ALTER COLUMN course_id TYPE VARCHAR USING course_id::text")
        )


def seed_courses() -> None:
    with SessionLocal() as session:
        existing = {row[0] for row in session.execute(select(Course.id)).all()}
        for course_data in COURSE_SEED:
            if course_data["id"] in existing:
                continue
            course = Course(
                id=course_data["id"],
                name=course_data["name"],
                tagline=course_data["tagline"],
                description=course_data["description"],
                price_cents=course_data["price_cents"],
                level=course_data["level"],
                duration_hours=course_data["duration_hours"],
                image_path=course_data["image_path"],
            )
            session.add(course)
            session.flush()
            for m_pos, module_data in enumerate(course_data["modules"]):
                module = CourseModule(course_id=course.id, title=module_data["title"], position=m_pos)
                session.add(module)
                session.flush()
                for l_pos, lesson_data in enumerate(module_data["lessons"]):
                    lesson = CourseLesson(
                        module_id=module.id,
                        title=lesson_data["title"],
                        duration_min=lesson_data["duration_min"],
                        video_key=f"videos/{course.id}/{m_pos + 1}-{l_pos + 1}.mp4",
                        is_free=lesson_data.get("free", False),
                        position=l_pos,
                    )
                    session.add(lesson)
        session.commit()


# ---------- Users ----------


def create_user(email: str, hashed_password: str) -> User:
    with SessionLocal() as session:
        existing = session.scalar(select(User).where(User.email == email))
        if existing:
            raise ValueError("El email ya está registrado")
        user = User(email=email, hashed_password=hashed_password)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def get_user_by_email(email: str) -> Optional[User]:
    with SessionLocal() as session:
        return session.scalar(select(User).where(User.email == email))


def get_user_by_id(user_id: int) -> Optional[User]:
    with SessionLocal() as session:
        return session.get(User, user_id)


# ---------- Leads ----------


def create_lead(
    service_category: str,
    contact_name: str,
    email: str,
    company_size: str,
    message: str,
) -> Lead:
    """Persiste el lead en estado `recibido` y su `quote_params` v1 (decisión 002 §5.3)."""
    with SessionLocal() as session:
        lead = Lead(
            service_category=service_category,
            contact_name=contact_name,
            email=email,
            company_size=company_size,
            message=message,
            status=LEAD_STATUS_RECIBIDO,
            assigned_agent_id=None,
        )
        session.add(lead)
        session.flush()
        session.add(
            QuoteParams(
                lead_id=lead.id,
                service_category=service_category,
                params={
                    "source": "lead_panel",
                    "message": message,
                    "company_size": company_size,
                },
                version=1,
            )
        )
        session.commit()
        session.refresh(lead)
        return lead


def get_lead(lead_id: int) -> Optional[Lead]:
    with SessionLocal() as session:
        return session.get(Lead, lead_id)


def get_lead_quote(lead_id: int) -> Optional[Quote]:
    """Cotización activa del lead (1 por lead); None si no existe."""
    with SessionLocal() as session:
        return session.scalar(select(Quote).where(Quote.lead_id == lead_id))


def get_lead_quote_params(lead_id: int) -> Optional[QuoteParams]:
    """Parámetros del lead (la versión más reciente); None si no hay fila."""
    with SessionLocal() as session:
        return session.scalar(
            select(QuoteParams)
            .where(QuoteParams.lead_id == lead_id)
            .order_by(QuoteParams.version.desc())
            .limit(1)
        )


def list_leads(
    status_filter: Optional[str] = None,
    service_category: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[List[Lead], int]:
    """Lista leads con filtros combinables; orden `created_at` desc (002-02)."""
    with SessionLocal() as session:
        stmt = select(Lead)
        count_stmt = select(func.count(Lead.id))
        if status_filter:
            stmt = stmt.where(Lead.status == status_filter)
            count_stmt = count_stmt.where(Lead.status == status_filter)
        if service_category:
            stmt = stmt.where(Lead.service_category == service_category)
            count_stmt = count_stmt.where(Lead.service_category == service_category)
        if date_from:
            start = datetime.combine(date_from, datetime.min.time())
            stmt = stmt.where(Lead.created_at >= start)
            count_stmt = count_stmt.where(Lead.created_at >= start)
        if date_to:
            end = datetime.combine(date_to, datetime.max.time())
            stmt = stmt.where(Lead.created_at <= end)
            count_stmt = count_stmt.where(Lead.created_at <= end)
        total = session.scalar(count_stmt) or 0
        items = session.scalars(
            stmt.order_by(Lead.created_at.desc(), Lead.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(items), total


# ---------- Courses ----------


def list_active_courses() -> List[Course]:
    with SessionLocal() as session:
        return list(session.scalars(select(Course).where(Course.is_active == True)).all())  # noqa: E712


def get_course(course_id: str) -> Optional[Course]:
    with SessionLocal() as session:
        return session.get(Course, course_id)


def get_course_modules(course_id: str) -> List[CourseModule]:
    with SessionLocal() as session:
        return list(
            session.scalars(
                select(CourseModule).where(CourseModule.course_id == course_id).order_by(CourseModule.position)
            ).all()
        )


def get_module_lessons(module_id: int) -> List[CourseLesson]:
    with SessionLocal() as session:
        return list(
            session.scalars(
                select(CourseLesson).where(CourseLesson.module_id == module_id).order_by(CourseLesson.position)
            ).all()
        )


def get_lesson(lesson_id: int) -> Optional[CourseLesson]:
    with SessionLocal() as session:
        return session.get(CourseLesson, lesson_id)


def count_course_lessons(course_id: str) -> int:
    with SessionLocal() as session:
        module_ids = session.scalars(select(CourseModule.id).where(CourseModule.course_id == course_id)).all()
        if not module_ids:
            return 0
        return len(
            session.scalars(select(CourseLesson.id).where(CourseLesson.module_id.in_(module_ids))).all()
        )


# ---------- Enrollments ----------


def grant_enrollment(user_id: int, course_id: str, source: str = "purchase") -> None:
    with SessionLocal() as session:
        existing = session.scalar(
            select(Enrollment).where(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
        )
        if existing:
            return
        session.add(Enrollment(user_id=user_id, course_id=course_id, source=source))
        try:
            session.commit()
        except IntegrityError:
            session.rollback()


def get_enrolled_course_ids(user_id: int) -> List[str]:
    with SessionLocal() as session:
        return list(session.scalars(select(Enrollment.course_id).where(Enrollment.user_id == user_id)).all())


def has_enrollment(user_id: int, course_id: str) -> bool:
    with SessionLocal() as session:
        return (
            session.scalar(
                select(Enrollment.id).where(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
            )
            is not None
        )


def user_has_lesson_access(user_id: int, lesson_id: int) -> bool:
    """Acceso si la lección es gratuita o el usuario tiene enrollment en el curso."""
    with SessionLocal() as session:
        lesson = session.get(CourseLesson, lesson_id)
        if not lesson:
            return False
        if lesson.is_free:
            return True
        module = session.get(CourseModule, lesson.module_id)
        if not module:
            return False
        return (
            session.scalar(
                select(Enrollment.id).where(
                    Enrollment.user_id == user_id, Enrollment.course_id == module.course_id
                )
            )
            is not None
        )


# ---------- Progress ----------


def upsert_lesson_progress(
    user_id: int, lesson_id: int, status: LessonStatus, position_seconds: int
) -> LessonProgress:
    with SessionLocal() as session:
        progress = session.scalar(
            select(LessonProgress).where(
                LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson_id
            )
        )
        if progress is None:
            progress = LessonProgress(user_id=user_id, lesson_id=lesson_id)
            session.add(progress)
        progress.status = status
        progress.position_seconds = position_seconds
        progress.completed_at = datetime.utcnow() if status == LessonStatus.completed else None
        session.commit()
        session.refresh(progress)
        return progress


def get_course_progress(user_id: int, course_id: str) -> List[LessonProgress]:
    with SessionLocal() as session:
        module_ids = session.scalars(select(CourseModule.id).where(CourseModule.course_id == course_id)).all()
        if not module_ids:
            return []
        lesson_ids = session.scalars(
            select(CourseLesson.id).where(CourseLesson.module_id.in_(module_ids))
        ).all()
        if not lesson_ids:
            return []
        return list(
            session.scalars(
                select(LessonProgress).where(
                    LessonProgress.user_id == user_id, LessonProgress.lesson_id.in_(lesson_ids)
                )
            ).all()
        )


def count_completed_lessons(user_id: int, course_id: str) -> int:
    return sum(1 for p in get_course_progress(user_id, course_id) if p.status == LessonStatus.completed)


# ---------- Purchases ----------


def create_purchase_record(stripe_session_id: str, course_id: str, customer_email: str, video_key: str) -> None:
    with SessionLocal() as session:
        purchase = Purchase(
            stripe_session_id=stripe_session_id,
            course_id=course_id,
            customer_email=customer_email,
            payment_status=PurchaseStatus.pending,
            video_key=video_key,
        )
        session.add(purchase)
        session.commit()


def get_purchase_by_session(session_id: str) -> Optional[Purchase]:
    with SessionLocal() as session:
        return session.get(Purchase, session_id)


def get_purchase_by_payment_intent(payment_intent_id: str) -> Optional[Purchase]:
    with SessionLocal() as session:
        return session.scalar(
            select(Purchase).where(Purchase.payment_intent_id == payment_intent_id)
        )


def set_purchase_payment_intent(session_id: str, payment_intent_id: str) -> None:
    with SessionLocal() as session:
        purchase = session.get(Purchase, session_id)
        if purchase:
            purchase.payment_intent_id = payment_intent_id
            session.commit()


def mark_event_processed(event_id: str, event_type: Optional[str] = None) -> bool:
    with SessionLocal() as session:
        session.add(ProcessedWebhookEvent(event_id=event_id, type=event_type))
        try:
            session.commit()
            return True
        except IntegrityError:
            session.rollback()
            return False


def update_purchase_status(session_id: str, status: PurchaseStatus) -> None:
    with SessionLocal() as session:
        purchase = session.get(Purchase, session_id)
        if purchase:
            purchase.payment_status = status
            session.commit()


def get_completed_purchase(course_id: str, customer_email: str) -> Optional[Purchase]:
    with SessionLocal() as session:
        stmt = select(Purchase).where(
            Purchase.course_id == course_id,
            Purchase.customer_email == customer_email,
            Purchase.payment_status == PurchaseStatus.complete,
        )
        return session.scalar(stmt)


def grant_enrollment_from_purchase(session_id: str) -> None:
    """Cuando un pago se completa: enlaza el enrollment con el usuario (si existe)."""
    with SessionLocal() as session:
        purchase = session.get(Purchase, session_id)
        if not purchase or purchase.payment_status != PurchaseStatus.complete:
            return
        user = session.scalar(select(User).where(User.email == purchase.customer_email))
        if not user:
            return
        course_id = purchase.course_id
        existing = session.scalar(
            select(Enrollment).where(Enrollment.user_id == user.id, Enrollment.course_id == course_id)
        )
        if not existing:
            session.add(Enrollment(user_id=user.id, course_id=course_id, source="purchase"))
            try:
                session.commit()
            except IntegrityError:
                session.rollback()


# ---------- Admin: CRUD cursos ----------


def create_course(
    course_id: str,
    name: str,
    tagline: str = "",
    description: str = "",
    price_cents: int = 0,
    currency: str = "usd",
    level: str = "",
    duration_hours: int = 0,
    image_path: str = "",
) -> Course:
    with SessionLocal() as session:
        if session.get(Course, course_id):
            raise ValueError(f"Ya existe un curso con id '{course_id}'")
        course = Course(
            id=course_id,
            name=name,
            tagline=tagline,
            description=description,
            price_cents=price_cents,
            currency=currency,
            level=level,
            duration_hours=duration_hours,
            image_path=image_path,
        )
        session.add(course)
        session.commit()
        session.refresh(course)
        return course


def update_course(course_id: str, **fields) -> Optional[Course]:
    allowed = {
        "name", "tagline", "description", "price_cents", "currency",
        "level", "duration_hours", "image_path", "is_active",
    }
    with SessionLocal() as session:
        course = session.get(Course, course_id)
        if not course:
            return None
        for key, value in fields.items():
            if key in allowed and value is not None:
                setattr(course, key, value)
        session.commit()
        session.refresh(course)
        return course


def delete_course(course_id: str) -> bool:
    """Borrado en cascada: lecciones -> módulos -> curso. Protege cursos con enrollments."""
    with SessionLocal() as session:
        course = session.get(Course, course_id)
        if not course:
            return False
        has_enrollments = session.scalar(
            select(Enrollment.id).where(Enrollment.course_id == course_id)
        )
        if has_enrollments:
            raise ValueError("No se puede eliminar: el curso tiene usuarios inscritos. Desactívalo en su lugar.")
        modules = session.scalars(select(CourseModule).where(CourseModule.course_id == course_id)).all()
        for module in modules:
            lessons = session.scalars(select(CourseLesson).where(CourseLesson.module_id == module.id)).all()
            for lesson in lessons:
                progress = session.scalars(select(LessonProgress).where(LessonProgress.lesson_id == lesson.id)).all()
                for p in progress:
                    session.delete(p)
                session.delete(lesson)
            session.delete(module)
        session.delete(course)
        session.commit()
        return True


# ---------- Admin: CRUD módulos ----------


def create_module(course_id: str, title: str, position: int = 0) -> CourseModule:
    with SessionLocal() as session:
        if not session.get(Course, course_id):
            raise ValueError(f"Curso '{course_id}' no encontrado")
        module = CourseModule(course_id=course_id, title=title, position=position)
        session.add(module)
        session.commit()
        session.refresh(module)
        return module


def update_module(module_id: int, **fields) -> Optional[CourseModule]:
    with SessionLocal() as session:
        module = session.get(CourseModule, module_id)
        if not module:
            return None
        for key in ("title", "position"):
            if key in fields and fields[key] is not None:
                setattr(module, key, fields[key])
        session.commit()
        session.refresh(module)
        return module


def delete_module(module_id: int) -> bool:
    with SessionLocal() as session:
        module = session.get(CourseModule, module_id)
        if not module:
            return False
        lessons = session.scalars(select(CourseLesson).where(CourseLesson.module_id == module_id)).all()
        for lesson in lessons:
            progress = session.scalars(select(LessonProgress).where(LessonProgress.lesson_id == lesson.id)).all()
            for p in progress:
                session.delete(p)
            session.delete(lesson)
        session.delete(module)
        session.commit()
        return True


# ---------- Admin: CRUD lecciones ----------


def create_lesson(
    module_id: int,
    title: str,
    duration_min: int = 0,
    video_key: str = "",
    is_free: bool = False,
    position: int = 0,
) -> CourseLesson:
    with SessionLocal() as session:
        if not session.get(CourseModule, module_id):
            raise ValueError(f"Módulo {module_id} no encontrado")
        lesson = CourseLesson(
            module_id=module_id,
            title=title,
            duration_min=duration_min,
            video_key=video_key,
            is_free=is_free,
            position=position,
        )
        session.add(lesson)
        session.commit()
        session.refresh(lesson)
        return lesson


def update_lesson(lesson_id: int, **fields) -> Optional[CourseLesson]:
    allowed = {"title", "duration_min", "video_key", "is_free", "position"}
    with SessionLocal() as session:
        lesson = session.get(CourseLesson, lesson_id)
        if not lesson:
            return None
        for key, value in fields.items():
            if key in allowed and value is not None:
                setattr(lesson, key, value)
        session.commit()
        session.refresh(lesson)
        return lesson


def delete_lesson(lesson_id: int) -> bool:
    with SessionLocal() as session:
        lesson = session.get(CourseLesson, lesson_id)
        if not lesson:
            return False
        progress = session.scalars(select(LessonProgress).where(LessonProgress.lesson_id == lesson_id)).all()
        for p in progress:
            session.delete(p)
        session.delete(lesson)
        session.commit()
        return True


# ---------- Admin: enrollments manuales ----------


def grant_enrollment_by_email(email: str, course_id: str, source: str = "manual") -> None:
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == email))
        if not user:
            raise ValueError(f"Usuario '{email}' no encontrado")
        if not session.get(Course, course_id):
            raise ValueError(f"Curso '{course_id}' no encontrado")
        existing = session.scalar(
            select(Enrollment).where(Enrollment.user_id == user.id, Enrollment.course_id == course_id)
        )
        if existing:
            return
        session.add(Enrollment(user_id=user.id, course_id=course_id, source=source))
        try:
            session.commit()
        except IntegrityError:
            session.rollback()


def revoke_enrollment_by_email(email: str, course_id: str) -> bool:
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == email))
        if not user:
            return False
        enrollment = session.scalar(
            select(Enrollment).where(Enrollment.user_id == user.id, Enrollment.course_id == course_id)
        )
        if not enrollment:
            return False
        session.delete(enrollment)
        session.commit()
        return True


def revoke_enrollment(user_id: int, course_id: str) -> bool:
    with SessionLocal() as session:
        enrollment = session.scalar(
            select(Enrollment).where(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
        )
        if not enrollment:
            return False
        session.delete(enrollment)
        session.commit()
        return True


def list_enrollments() -> list:
    with SessionLocal() as session:
        rows = session.execute(
            select(Enrollment, User).join(User, User.id == Enrollment.user_id)
        ).all()
        return [
            {
                "enrollment_id": e.id,
                "user_email": u.email,
                "course_id": e.course_id,
                "source": e.source,
                "granted_at": e.granted_at,
            }
            for e, u in rows
        ]


def set_admin(email: str, is_admin: bool = True) -> bool:
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == email))
        if not user:
            return False
        user.is_admin = is_admin
        session.commit()
        return True

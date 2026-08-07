import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import Column, DateTime, Enum as SqlEnum, String, create_engine, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from backend.config import get_settings
from backend.schemas import CourseId, PurchaseStatus

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = get_settings().database_url
CONNECT_ARGS = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=CONNECT_ARGS)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Purchase(Base):
    __tablename__ = "purchases"

    stripe_session_id = Column(String, primary_key=True, index=True)
    course_id = Column(SqlEnum(CourseId), nullable=False)
    customer_email = Column(String, nullable=False, index=True)
    payment_status = Column(SqlEnum(PurchaseStatus), nullable=False, default=PurchaseStatus.pending)
    video_key = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db() -> None:
    if DATABASE_URL.startswith("sqlite"):
        data_dir = BASE_DIR / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def create_purchase_record(stripe_session_id: str, course_id: CourseId, customer_email: str, video_key: str) -> None:
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


def update_purchase_status(session_id: str, status: PurchaseStatus) -> None:
    with SessionLocal() as session:
        purchase = session.get(Purchase, session_id)
        if purchase:
            purchase.payment_status = status
            session.commit()


def get_completed_purchase(course_id: CourseId, customer_email: str) -> Optional[Purchase]:
    with SessionLocal() as session:
        stmt = select(Purchase).where(
            Purchase.course_id == course_id,
            Purchase.customer_email == customer_email,
            Purchase.payment_status == PurchaseStatus.complete,
        )
        return session.scalar(stmt)

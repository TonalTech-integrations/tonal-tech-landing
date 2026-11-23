import logging

from backend.schemas import PurchaseStatus
from backend.services.persistence import (
    Enrollment,
    SessionLocal,
    create_purchase_record,
    create_user,
    hash_password,
    select,
)
from backend.services.stripe import handle_event


def _count_enrollments(user_id: int, course_id: str) -> int:
    with SessionLocal() as session:
        return len(
            session.scalars(
                select(Enrollment).where(
                    Enrollment.user_id == user_id, Enrollment.course_id == course_id
                )
            ).all()
        )


def _complete_checkout(session_id: str, payment_intent_id: str) -> None:
    handle_event(
        {
            "id": f"evt_completed_{session_id}",
            "type": "checkout.session.completed",
            "data": {"object": {"id": session_id, "payment_intent": payment_intent_id}},
        }
    )


def test_charge_refunded_revokes_enrollment(db):
    email = "buyer@test.com"
    user = create_user(email, hash_password("password123"))
    create_purchase_record("cs_refund_1", "plc-industrial", email, "videos/plc-industrial")
    _complete_checkout("cs_refund_1", "pi_refund_1")
    assert _count_enrollments(user.id, "plc-industrial") == 1

    result = handle_event(
        {
            "id": "evt_refund_1",
            "type": "charge.refunded",
            "data": {"object": {"id": "ch_refund_1", "payment_intent": "pi_refund_1"}},
        }
    )

    assert result["received"] is True
    assert _count_enrollments(user.id, "plc-industrial") == 0
    purchase = db.get_purchase_by_session("cs_refund_1")
    assert purchase.payment_status == PurchaseStatus.refunded
    with SessionLocal() as session:
        assert session.get(db.ProcessedWebhookEvent, "evt_refund_1") is not None


def test_async_payment_failed_marks_purchase_failed(db):
    email = "buyer@test.com"
    user = create_user(email, hash_password("password123"))
    create_purchase_record("cs_failed_1", "plc-industrial", email, "videos/plc-industrial")

    result = handle_event(
        {
            "id": "evt_failed_1",
            "type": "checkout.session.async_payment_failed",
            "data": {"object": {"id": "cs_failed_1"}},
        }
    )

    assert result["received"] is True
    purchase = db.get_purchase_by_session("cs_failed_1")
    assert purchase.payment_status == PurchaseStatus.failed
    assert _count_enrollments(user.id, "plc-industrial") == 0


def test_webhook_event_processed_once(db):
    create_purchase_record("cs_dup_1", "plc-industrial", "buyer@test.com", "videos/plc-industrial")
    event = {
        "id": "evt_dup_1",
        "type": "checkout.session.expired",
        "data": {"object": {"id": "cs_dup_1"}},
    }

    first = handle_event(event)
    second = handle_event(event)

    assert first["received"] is True
    assert second["received"] is True
    assert second["duplicate"] is True


def test_refund_without_purchase_logs_and_returns_ok(db, caplog):
    with caplog.at_level(logging.WARNING):
        result = handle_event(
            {
                "id": "evt_refund_orphan_1",
                "type": "charge.refunded",
                "data": {"object": {"id": "ch_orphan_1", "payment_intent": "pi_orphan_1"}},
            }
        )

    assert result["received"] is True
    assert any("refund" in record.message.lower() for record in caplog.records)


def test_revoke_enrollment_keeps_lesson_progress(db):
    email = "buyer@test.com"
    user = create_user(email, hash_password("password123"))
    create_purchase_record("cs_progress_1", "plc-industrial", email, "videos/plc-industrial")
    _complete_checkout("cs_progress_1", "pi_progress_1")

    with SessionLocal() as session:
        lesson = session.scalars(select(db.CourseLesson).limit(1)).one()
        session.add(
            db.LessonProgress(
                user_id=user.id,
                lesson_id=lesson.id,
                status=db.LessonStatus.in_progress,
                position_seconds=120,
            )
        )
        session.commit()
        lesson_id = lesson.id

    handle_event(
        {
            "id": "evt_refund_progress_1",
            "type": "charge.refunded",
            "data": {"object": {"id": "ch_progress_1", "payment_intent": "pi_progress_1"}},
        }
    )

    assert _count_enrollments(user.id, "plc-industrial") == 0
    with SessionLocal() as session:
        progress = session.scalars(
            select(db.LessonProgress).where(db.LessonProgress.user_id == user.id)
        ).all()
    assert len(progress) == 1
    assert progress[0].lesson_id == lesson_id


def test_processed_event_stores_type(db):
    from backend.services.persistence import ProcessedWebhookEvent, SessionLocal

    db.mark_event_processed("evt_type_1", "charge.refunded")

    with SessionLocal() as session:
        assert session.get(ProcessedWebhookEvent, "evt_type_1").type == "charge.refunded"

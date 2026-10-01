import threading

from backend.schemas import PurchaseStatus
from backend.services.persistence import (
    Enrollment,
    SessionLocal,
    create_purchase_record,
    create_user,
    grant_enrollment_by_email,
    grant_enrollment_from_purchase,
    hash_password,
    select,
    update_purchase_status,
)


def _count_enrollments(user_id: int, course_id: str) -> int:
    with SessionLocal() as session:
        return len(
            session.scalars(
                select(Enrollment).where(
                    Enrollment.user_id == user_id, Enrollment.course_id == course_id
                )
            ).all()
        )


def test_grant_enrollment_idempotent_under_concurrency(db):
    email = "race@test.com"
    user = create_user(email, hash_password("password123"))
    errors = []
    barrier = threading.Barrier(2)

    def worker():
        try:
            barrier.wait()
            grant_enrollment_by_email(email, "plc-industrial")
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
    assert _count_enrollments(user.id, "plc-industrial") == 1


def test_grant_enrollment_from_purchase_handles_duplicate(db):
    email = "buyer@test.com"
    user = create_user(email, hash_password("password123"))
    create_purchase_record("cs_dup_1", "plc-industrial", email, "videos/plc-industrial")
    update_purchase_status("cs_dup_1", PurchaseStatus.complete)
    grant_enrollment_from_purchase("cs_dup_1")
    grant_enrollment_from_purchase("cs_dup_1")
    assert _count_enrollments(user.id, "plc-industrial") == 1

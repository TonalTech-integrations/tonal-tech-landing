import time


def _lesson_with_access(db, auth_headers):
    headers = auth_headers()
    user = db.get_user_by_email("user@test.com")
    db.grant_enrollment(user.id, "plc-industrial")
    with db.SessionLocal() as session:
        lesson = session.query(db.CourseLesson).filter(db.CourseLesson.video_key.isnot(None)).first()
        session.expunge(lesson)
    return headers, lesson


def test_stream_url_returns_expires_at(client, db, auth_headers):
    headers, lesson = _lesson_with_access(db, auth_headers)
    before = int(time.time())

    response = client.get(f"/lessons/{lesson.id}/stream-url", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["stream_url"]
    assert before + 800 <= body["expires_at"] <= int(time.time()) + 900

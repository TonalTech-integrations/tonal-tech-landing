import os
import tempfile

import pytest

_TMP_DIR = tempfile.mkdtemp(prefix="tonal-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DIR}/test.db"
os.environ["PAYMENTS_MOCK"] = "true"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-32-chars-minimum-1234"
os.environ["STRIPE_SECRET_KEY"] = "sk_test_dummy"
os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_dummy"
os.environ["STRIPE_PRICE_ID"] = "price_global_test"
os.environ["AWS_ACCESS_KEY_ID"] = "dummy"
os.environ["AWS_SECRET_ACCESS_KEY"] = "dummy"
os.environ["AWS_S3_BUCKET"] = "dummy-bucket"


@pytest.fixture()
def db():
    from backend.services import persistence
    from backend.services.persistence import Base, engine, init_db

    Base.metadata.drop_all(bind=engine)
    init_db()
    yield persistence
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db):
    from fastapi.testclient import TestClient

    from backend.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth_headers():
    def _make(email="user@test.com", password="password123", is_admin=False):
        from backend.routers.auth import create_access_token
        from backend.services.persistence import create_user, hash_password, set_admin

        user = create_user(email, hash_password(password))
        if is_admin:
            set_admin(email, True)
        token = create_access_token({"sub": str(user.id)})
        return {"Authorization": f"Bearer {token}"}

    return _make

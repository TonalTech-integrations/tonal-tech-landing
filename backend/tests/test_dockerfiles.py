from pathlib import Path

BACKEND_DOCKERFILE = Path(__file__).resolve().parents[2] / "backend" / "Dockerfile"
FRONTEND_DOCKERFILE = Path(__file__).resolve().parents[2] / "Dockerfile.frontend"


def test_backend_dockerfile_has_no_copy_env():
    content = BACKEND_DOCKERFILE.read_text()

    assert "COPY backend/ .env" not in content


def test_backend_dockerfile_no_reload():
    content = BACKEND_DOCKERFILE.read_text()
    cmd_lines = [line for line in content.splitlines() if line.startswith("CMD")]

    assert cmd_lines
    assert "uvicorn" in cmd_lines[0]
    assert "--reload" not in cmd_lines[0]
    assert "--workers" in cmd_lines[0]


def test_backend_dockerfile_runs_as_non_root():
    content = BACKEND_DOCKERFILE.read_text()
    user_lines = [line for line in content.splitlines() if line.startswith("USER")]

    assert user_lines
    assert all(line.split()[1] != "root" for line in user_lines)


def test_frontend_dockerfile_serves_static_out():
    content = FRONTEND_DOCKERFILE.read_text()

    assert "nginx" in content
    assert "out" in content
    assert "pnpm dev" not in content

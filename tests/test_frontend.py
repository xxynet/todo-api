from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_frontend_is_served_when_a_build_is_available(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<h1>TODO</h1>", encoding="utf-8")
    (dist_dir / "app.js").write_text("console.log('todo')", encoding="utf-8")

    app = create_app(Settings(frontend_dist_dir=dist_dir))
    with TestClient(app) as client:
        assert client.get("/").text == "<h1>TODO</h1>"
        script_response = client.get("/app.js")
        assert script_response.text == "console.log('todo')"
        assert script_response.headers["content-type"] == "application/javascript"
        assert client.get("/todos/today").text == "<h1>TODO</h1>"
        assert client.get("/missing.js").status_code == 404
        assert client.get("/api/v1/health").json() == {"status": "ok"}
        assert client.get("/api/v1/missing").status_code == 404


def test_frontend_is_not_mounted_without_an_index_file(tmp_path: Path) -> None:
    app = create_app(Settings(frontend_dist_dir=tmp_path))

    with TestClient(app) as client:
        assert client.get("/").status_code == 404

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "version-aware-doc-assistant",
    }
def test_application_ui_is_available() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Version-Aware Documentation Assistant" in response.text
    assert "Ask the documentation agent" in response.text
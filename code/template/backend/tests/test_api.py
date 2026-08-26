from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_user_can_register_and_manage_own_todos() -> None:
    with TestClient(app) as client:
        email = f"ana-{uuid4().hex}@example.com"
        register = client.post(
            "/auth/register", json={"email": email, "password": "senha-segura"}
        )
        assert register.status_code == 201
        headers = {"Authorization": f"Bearer {register.json()['access_token']}"}

        profile = client.patch("/profile", json={"name": "Ana Silva", "email": email}, headers=headers)
        assert profile.status_code == 200
        assert profile.json()["name"] == "Ana Silva"

        created = client.post(
            "/todos",
            json={
                "title": "Estudar FastAPI",
                "description": "Revisar autenticação e rotas.",
                "scheduled_time": "09:30",
                "repeats_daily": True,
            },
            headers=headers,
        )
        assert created.status_code == 201
        todo_id = created.json()["id"]
        assert created.json()["scheduled_time"] == "09:30"
        assert created.json()["repeats_daily"] is True

        updated = client.patch(f"/todos/{todo_id}", json={"completed": True}, headers=headers)
        assert updated.status_code == 200
        assert updated.json()["completed"] is True

        listed = client.get("/todos", headers=headers)
        assert [item["title"] for item in listed.json()] == ["Estudar FastAPI"]

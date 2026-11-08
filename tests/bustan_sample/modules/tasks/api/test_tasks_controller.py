from collections.abc import Callable

from bustan.testing import AsgiTestClient

from bustan_sample.modules.tasks.application.on_user_registered import STARTER_TITLE
from bustan_sample.platform.clock import FixedClock

SignUp = Callable[[str], dict[str, str]]
UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


def test_a_new_user_gets_a_starter_task(
    client: AsgiTestClient, sign_up: SignUp
) -> None:
    # sign_up waits for the event handler that adds the task in the background.
    tasks = client.get("/tasks", headers=sign_up("ada@example.com")).json()
    assert [task["title"] for task in tasks] == [STARTER_TITLE]
    assert tasks[0]["status"] == "todo"


def test_each_route_needs_a_token(client: AsgiTestClient) -> None:
    responses = [
        client.get("/tasks"),
        client.post("/tasks", json={"title": "a"}),
        client.get(f"/tasks/{UNKNOWN_ID}"),
        client.patch(f"/tasks/{UNKNOWN_ID}", json={"status": "done"}),
        client.delete(f"/tasks/{UNKNOWN_ID}"),
    ]
    assert [response.status_code for response in responses] == [401] * 5


def test_create_returns_201_with_location_and_body(
    client: AsgiTestClient, sign_up: SignUp, clock: FixedClock
) -> None:
    ada = sign_up("ada@example.com")
    response = client.post(
        "/tasks", headers=ada, json={"title": "write the skill", "due_on": "2026-02-01"}
    )
    body = response.json()
    assert response.status_code == 201
    assert response.headers["location"] == f"/tasks/{body['id']}"
    assert body["status"] == "todo"
    assert body["due_on"] == "2026-02-01"
    assert body["created_at"] == clock.now().isoformat().replace("+00:00", "Z")


def test_get_returns_the_created_task(client: AsgiTestClient, sign_up: SignUp) -> None:
    ada = sign_up("ada@example.com")
    created = client.post("/tasks", headers=ada, json={"title": "a"}).json()
    response = client.get(f"/tasks/{created['id']}", headers=ada)
    assert response.status_code == 200
    assert response.json() == created


def test_list_filters_on_the_status_query(
    client: AsgiTestClient, sign_up: SignUp
) -> None:
    ada = sign_up("ada@example.com")
    client.post("/tasks", headers=ada, json={"title": "open"})
    done = client.post("/tasks", headers=ada, json={"title": "done"}).json()
    client.patch(f"/tasks/{done['id']}", headers=ada, json={"status": "done"})
    everything = client.get("/tasks", headers=ada).json()
    only_done = client.get("/tasks", headers=ada, params={"status": "done"}).json()
    assert [task["title"] for task in everything] == [STARTER_TITLE, "open", "done"]
    assert [task["title"] for task in only_done] == ["done"]


def test_patch_with_null_due_on_removes_the_due_date(
    client: AsgiTestClient, sign_up: SignUp
) -> None:
    ada = sign_up("ada@example.com")
    created = client.post(
        "/tasks", headers=ada, json={"title": "a", "due_on": "2026-02-01"}
    ).json()
    response = client.patch(
        f"/tasks/{created['id']}", headers=ada, json={"due_on": None}
    )
    assert response.status_code == 200
    assert response.json()["due_on"] is None
    assert response.json()["title"] == "a"


def test_delete_returns_204_and_then_404(
    client: AsgiTestClient, sign_up: SignUp
) -> None:
    ada = sign_up("ada@example.com")
    created = client.post("/tasks", headers=ada, json={"title": "gone"}).json()
    deleted = client.delete(f"/tasks/{created['id']}", headers=ada)
    again = client.delete(f"/tasks/{created['id']}", headers=ada)
    assert deleted.status_code == 204
    assert again.status_code == 404


def test_an_unknown_id_returns_problem_details(
    client: AsgiTestClient, sign_up: SignUp
) -> None:
    response = client.get(f"/tasks/{UNKNOWN_ID}", headers=sign_up("ada@example.com"))
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == f"no task with id {UNKNOWN_ID}"


def test_invalid_input_returns_400(client: AsgiTestClient, sign_up: SignUp) -> None:
    ada = sign_up("ada@example.com")
    responses = [
        client.post("/tasks", headers=ada, json={"title": "   "}),
        client.post("/tasks", headers=ada, json={"title": "a", "owner": "x"}),
        client.get("/tasks/not-a-uuid", headers=ada),
        client.get("/tasks", headers=ada, params={"status": "archived"}),
    ]
    assert [response.status_code for response in responses] == [400] * 4


def test_a_user_cannot_see_or_change_the_tasks_of_another_user(
    client: AsgiTestClient, sign_up: SignUp
) -> None:
    ada, bob = sign_up("ada@example.com"), sign_up("bob@example.com")
    task = client.post("/tasks", headers=ada, json={"title": "private"}).json()
    path = f"/tasks/{task['id']}"
    bob_tasks = client.get("/tasks", headers=bob).json()
    assert [task["title"] for task in bob_tasks] == [STARTER_TITLE]
    assert client.get(path, headers=bob).status_code == 404
    assert client.patch(path, headers=bob, json={"status": "done"}).status_code == 404
    assert client.delete(path, headers=bob).status_code == 404
    assert client.get(path, headers=ada).json()["status"] == "todo"

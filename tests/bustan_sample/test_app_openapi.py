from bustan.testing import AsgiTestClient

from bustan_sample.app_main import create_asgi_app
from bustan_sample.app_openapi import DOCUMENT_PATH, SWAGGER_UI_PATH


def test_the_app_serves_the_document_and_swagger_ui() -> None:
    client = AsgiTestClient(create_asgi_app())
    document = client.get(DOCUMENT_PATH)
    ui = client.get(SWAGGER_UI_PATH)
    assert document.status_code == ui.status_code == 200
    assert document.json()["info"]["title"] == "bustan-sample"
    assert "text/html" in ui.headers["content-type"]

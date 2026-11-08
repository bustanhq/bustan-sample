from pathlib import Path

import pytest
import yaml

from bustan_sample.openapi_export import main

ROOT = Path(__file__).resolve().parents[2]


def test_the_committed_openapi_yaml_agrees_with_the_code() -> None:
    # If this test fails, run: uv run bustan-sample-openapi
    assert main(["--check", "--output", str(ROOT / "openapi.yaml")]) == 0


def test_the_document_has_each_route_the_schemas_and_the_bearer_scheme(
    tmp_path: Path,
) -> None:
    output = tmp_path / "openapi.yaml"
    assert main(["--output", str(output)]) == 0
    document = yaml.safe_load(output.read_text())
    assert set(document["paths"]) == {
        "/identity/register",
        "/identity/login",
        "/identity/logout",
        "/identity/me",
        "/tasks",
        "/tasks/{task_id}",
        "/health/live",
        "/health/ready",
    }
    assert {"TaskResponse", "UserResponse", "TokenResponse"} <= set(
        document["components"]["schemas"]
    )
    assert document["components"]["securitySchemes"]["bearer"]["scheme"] == "bearer"
    assert "security" not in document["paths"]["/identity/login"]["post"]
    assert document["paths"]["/tasks"]["get"]["security"] == [{"bearer": []}]


def test_check_fails_for_a_file_that_does_not_agree(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "openapi.yaml"
    output.write_text("openapi: 3.1.0\n")
    assert main(["--check", "--output", str(output)]) == 1
    assert "does not agree" in capsys.readouterr().err

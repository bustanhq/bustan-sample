from importlib.metadata import version

from bustan import DocumentBuilder, SwaggerOptions

DOCUMENT_PATH = "/docs/api"
SWAGGER_UI_PATH = "/docs/ui"


def swagger_options() -> SwaggerOptions:
    """Return the OpenAPI settings of the application.

    Bustan builds the document from the compiled routes, the Pydantic models
    and the Api decorators. The application serves the document at
    DOCUMENT_PATH and Swagger UI at SWAGGER_UI_PATH. The command
    bustan-sample-openapi writes the same document to openapi.yaml.
    """
    document = (
        DocumentBuilder()
        .set_title("bustan-sample")
        .set_description(
            "Tasks with recurrence for each user, and the identity routes that "
            "give and revoke the bearer tokens."
        )
        .set_version(version("bustan-sample"))
        .add_bearer_auth()
    )
    return SwaggerOptions(
        document_builder=document, path=DOCUMENT_PATH, swagger_ui_path=SWAGGER_UI_PATH
    )

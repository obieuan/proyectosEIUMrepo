import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    api_base_url: str
    api_token: str
    request_timeout: int
    default_limit: int
    max_pages: int
    secret_key: str
    app_url: str
    azure_client_id: str
    azure_client_secret: str
    azure_tenant_id: str
    azure_redirect_uri: str
    super_admin_email: str


def load_settings() -> Settings:
    return Settings(
        api_base_url=os.environ.get(
            "API_BASE_URL",
            "http://127.0.0.1:8000/api/v1/proyectos/consulta",
        ),
        api_token=os.environ.get("API_TOKEN", ""),
        request_timeout=int(os.environ.get("API_TIMEOUT", "15")),
        default_limit=int(os.environ.get("API_LIMIT", "24")),
        max_pages=int(os.environ.get("API_MAX_PAGES", "10")),
        secret_key=os.environ.get("APP_SECRET_KEY", ""),
        app_url=os.environ.get("APP_URL", "http://localhost:5000"),
        azure_client_id=os.environ.get("AZURE_CLIENT_ID", ""),
        azure_client_secret=os.environ.get("AZURE_CLIENT_SECRET", ""),
        azure_tenant_id=os.environ.get("AZURE_TENANT_ID", ""),
        azure_redirect_uri=os.environ.get("AZURE_REDIRECT_URI", ""),
        super_admin_email=os.environ.get("SUPER_ADMIN_EMAIL", ""),
    )

from typing import Annotated, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field, AnyUrl, BeforeValidator


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    APP_NAME: str = "Assistant0"
    API_PREFIX: str = "/api"
    APP_BASE_URL: str

    # Auth0
    AUTH0_DOMAIN: str
    AUTH0_CLIENT_ID: str
    AUTH0_CLIENT_SECRET: str
    AUTH0_SECRET: str

    # Auth0 Token Vault (for Gmail and other third-party APIs)
    # These credentials are for the custom API client that performs token exchange
    AUTH0_CUSTOM_API_CLIENT_ID: str = ""
    AUTH0_CUSTOM_API_CLIENT_SECRET: str = ""
    AUTH0_AUDIENCE: str = ""

    # Auth0 FGA
    FGA_STORE_ID: str
    FGA_CLIENT_ID: str
    FGA_CLIENT_SECRET: str
    FGA_API_URL: str = "https://api.us1.fga.dev"
    FGA_API_AUDIENCE: str = "https://api.us1.fga.dev/"
    FGA_API_TOKEN_ISSUER: str = "auth.fga.dev"
    FGA_AUTHORIZATION_MODEL_ID: str | None = None

    # Shop API
    SHOP_API_URL: str = ""
    SHOP_API_AUDIENCE: str = ""

    # Gmail API Configuration
    GMAIL_SCOPES: str = "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/gmail.compose"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def GMAIL_SCOPES_LIST(self) -> list[str]:
        """Parse Gmail scopes from space-separated string to list."""
        return [scope.strip() for scope in self.GMAIL_SCOPES.split() if scope.strip()]

    # OpenAI
    OPENAI_API_KEY: str

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Qdrant Vector Database
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_NAME: str = "reploom_documents"

    # LangGraph server
    LANGGRAPH_API_URL: str = "http://localhost:54367"
    LANGGRAPH_API_KEY: str = ""

    FRONTEND_HOST: str = "http://localhost:5173"
    BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = [
        "http://localhost:8000"
    ]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ALL_CORS_ORIGINS(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

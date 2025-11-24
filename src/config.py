import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, ValidationError
from .exceptions import ConfigurationError

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_FILE = "text2bpmn.log"

class Settings(BaseSettings):
    """
    Loads configuration from .env file, checking for type errors and missing values.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    OPENAI_API_KEY: str = Field(..., description="API key for OpenAI.")
    AZURE_ENDPOINT: str = Field(..., description="Azure OpenAI endpoint.")
    API_VERSION : str = Field("2025-01-01-preview", description="API version.")
    MODEL: str = Field('gpt-4.1', description="Model name.")
    TEMPERATURE: float = Field(0.7, description="Sampling temperature.")
    MAX_TOKENS: int = Field(2048, description="Maximum number of tokens.")
    LOG_LEVEL: str = Field("INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR).")

def load_settings() -> Settings:
    try:
        return Settings()  
    except ValidationError as e:
        raise ConfigurationError(
            "Invalid or missing configuration values:\n" + str(e)
        )

def get_api_key(settings: Settings) -> str:
    return settings.OPENAI_API_KEY

def get_model_config(settings: Settings) -> dict:
    return {
        "model": settings.MODEL,
        "azure_endpoint": settings.AZURE_ENDPOINT,
        "api_version": settings.API_VERSION,
        "temperature": settings.TEMPERATURE,
        "max_tokens": settings.MAX_TOKENS,
    }

def get_log_level(settings: Settings) -> str:
    return settings.LOG_LEVEL

def setup_logging(settings: Settings):
    level = getattr(logging, get_log_level(settings=settings), logging.INFO)
    
    logging.basicConfig(
        filename=LOG_FILE,
        filemode="w",
        level=level,
        format=LOG_FORMAT
    )
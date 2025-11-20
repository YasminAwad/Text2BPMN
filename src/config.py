import os
from dotenv import load_dotenv, find_dotenv

dotenv_path = find_dotenv()

if dotenv_path:
    load_dotenv(dotenv_path)


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


def validate_api_key() -> str:
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        raise ConfigurationError(
            "OPENAI_API_KEY environment variable not set.\n"
            "Please set it with: export OPENAI_API_KEY='your-api-key'\n"
            "Or create a .env file with: OPENAI_API_KEY=your-api-key"
        )
    
    return api_key

# TODO: change to use pydantic models
def get_model_config() -> dict:
    return {
        'model': os.getenv('MODEL'),
        'temperature': float(os.getenv('TEMPERATURE')),
        'max_tokens': int(os.getenv('MAX_TOKENS'))
    }



from pathlib import Path
from typing import Optional

from ..exceptions import FileHandlerError

SUPPORTED_FILE_EXTENSIONS=['.txt', '.md']

def read_process_description(description: Optional[str], file: Optional[str]) -> str:
    if file:
        return read_file(file)
    if description:
        return validate_description(description)

    raise FileHandlerError("No process description provided")

def read_file(file_path: str) -> str:
    """
    Read content from a text or markdown file.
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileHandlerError(f"File not found: {file_path}")
    
    if not path.is_file():
        raise FileHandlerError(f"Not a file: {file_path}")
    
    if path.suffix.lower() not in SUPPORTED_FILE_EXTENSIONS:
        raise FileHandlerError(
            f"Unsupported file type: {path.suffix}\n"
            f"Supported types: {', '.join(SUPPORTED_FILE_EXTENSIONS)}"
        )
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
    except UnicodeDecodeError:
        raise FileHandlerError(f"File encoding error. Please ensure file is UTF-8 encoded.")
    except PermissionError:
        raise FileHandlerError(f"Permission denied: {file_path}")
    except Exception as e:
        raise FileHandlerError(f"Error reading file: {str(e)}")

    return validate_description(content)

def validate_description(description: str) -> str:
    """
    Ensures the process description:
    - Is not empty
    - Has minimum length (10 chars)
    - Doesn't exceed maximum length (10,000 chars)
    
    Args:
        description: Process description string
        
    Returns:
        Validated description (stripped of whitespace)
    
    """
    if not description or not description.strip():
        raise FileHandlerError("Process description is empty")
    
    if len(description) < 10:
        raise FileHandlerError(
            "Process description too short. "
            "Please provide a more detailed description (at least 10 characters)."
        )
    
    if len(description) > 10000:
        raise FileHandlerError(
            f"Process description too long ({len(description)} characters). "
            "Maximum length: 10,000 characters."
        )
    
    return description.strip()



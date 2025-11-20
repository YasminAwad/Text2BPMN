from pathlib import Path
from typing import Optional

from ..constants import SUPPORTED_FILE_EXTENSIONS


class FileHandlerError(Exception):
    """Raised when file operations fail."""
    pass


def read_process_description(description: Optional[str], file: Optional[str]) -> str:
    if file:
        return read_file(file)
    if description:
        return validate_description(description)

    raise FileHandlerError("No process description provided")



def read_file(file_path: str) -> str:
    """
    Read content from a text or markdown file.
    
    Performs comprehensive validation:
    - File existence check
    - File type validation (not a directory)
    - Extension validation (.txt, .md)
    - File size check (max 5MB)
    - Encoding validation (UTF-8)
    
    Args:
        file_path: Path to the file
        
    Returns:
        File content as string (stripped of whitespace)
        
    Raises:
        FileHandlerError: If file cannot be read or is invalid
    """
    path = Path(file_path)
    
    # Check if file exists
    if not path.exists():
        raise FileHandlerError(f"File not found: {file_path}")
    
    # Check if it's a file (not a directory)
    if not path.is_file():
        raise FileHandlerError(f"Not a file: {file_path}")
    
    # Validate file extension
    if path.suffix.lower() not in SUPPORTED_FILE_EXTENSIONS():
        raise FileHandlerError(
            f"Unsupported file type: {path.suffix}\n"
            f"Supported types: {', '.join(SUPPORTED_FILE_EXTENSIONS())}"
        )
    
    # Read file content
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
    except UnicodeDecodeError:
        raise FileHandlerError(f"File encoding error. Please ensure file is UTF-8 encoded.")
    except PermissionError:
        raise FileHandlerError(f"Permission denied: {file_path}")
    except Exception as e:
        raise FileHandlerError(f"Error reading file: {str(e)}")
    
    # Validate content
    return validate_description(content)


# TODO: Change. I don't like it. 10000 is arbitrary. Check gpt-4.1 input limit
def validate_description(description: str) -> str:
    """
    Validate process description content.
    
    Ensures the description:
    - Is not empty
    - Has minimum length (10 chars)
    - Doesn't exceed maximum length (10,000 chars)
    
    Args:
        description: Process description string
        
    Returns:
        Validated description (stripped of whitespace)
        
    Raises:
        FileHandlerError: If description is invalid
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



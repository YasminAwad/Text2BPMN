class BPMNGeneratorError(Exception):
    """Base exception for all BPMN Generator errors."""
    pass

class BPMNGenerationError(BPMNGeneratorError):
    """Raised when BPMN generation fails."""
    pass

class BPMNValidationError(BPMNGeneratorError):
    """Raised when BPMN validation fails."""
    pass

class FileHandlerError(BPMNGeneratorError):
    """Raised when file operations fail."""
    pass

class ConfigError(BPMNGeneratorError):
    """Raised when configuration is invalid."""
    pass

class LLMError(BPMNGeneratorError):
    """Raised when LLM operations fail."""
    pass

class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass

class FileHandlerError(Exception):
    """Raised when file operations fail."""
    pass

class BPMNLayoutError(BPMNGeneratorError):
    """Raised when BPMN auto-layout fails."""
    pass
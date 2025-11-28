class BPMNGenerationError(Exception):
    """Raised when BPMN generation fails."""
    pass

class BPMNJsonError(BPMNGenerationError):
    """Raised when BPMN JSON is invalid or malformed."""
    pass

class BPMNValidationError(BPMNGenerationError):
    """Raised when BPMN validation fails."""
    pass

class FileHandlerError(BPMNGenerationError):
    """Raised when file operations fail."""
    pass

class LLMServiceError(BPMNGenerationError):
    """Raised when LLM operations fail."""
    pass

class DiagramError(BPMNGenerationError):
    """Raised when merging BPMN files fails."""
    pass

class BPMNLayoutError(DiagramError):
    """Raised when BPMN auto-layout fails."""
    pass

# TODO: Add more specific exceptions
# class AddLaneDiagramError(DiagramError):
# class MergeBPMNFilesError(DiagramError):
# etc.

class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass
from ..constants import REQUIRED_ELEMENTS
import re

class BPMNGenerationError(Exception):
    """Raised when BPMN generation or validation fails."""
    pass

class BPMNFileValidator:
    """Validates and cleans BPMN XML content."""

    REQUIRED_ELEMENTS = ["definitions", "process", "startEvent", "endEvent"]

    @staticmethod
    def clean_xml(xml: str) -> str:
        """
        Remove markdown code fences and extra whitespace from XML.
        
        Args:
            xml: Raw XML string
            
        Returns:
            Cleaned XML string
        """
        # Remove markdown code fences
        xml = re.sub(r'```xml\s*', '', xml)
        xml = re.sub(r'```\s*', '', xml)
        
        # Remove any leading/trailing whitespace
        xml = xml.strip()
        
        return xml

    @staticmethod
    def validate(xml: str) -> None:
        """
        Validate that XML contains required BPMN elements.
        
        Args:
            xml: BPMN XML string to validate
            
        Raises:
            BPMNGenerationError: If XML is invalid or missing required elements
        """
        if not xml:
            raise BPMNGenerationError("Empty XML content")
        
        # Check for XML declaration
        if not xml.startswith("<?xml"):
            raise BPMNGenerationError(
                "Missing XML declaration. BPMN file must start with <?xml version=\"1.0\"?>"
            )
        
        # Check for required BPMN elements
        for element in BPMNFileValidator.REQUIRED_ELEMENTS:
            if element not in xml:
                raise BPMNGenerationError(
                    f"Missing required BPMN element: <{element}>. "
                    f"A valid BPMN diagram must contain: {', '.join(BPMNFileValidator.REQUIRED_ELEMENTS)}"
                )
        
        # Basic XML structure check
        if xml.count('<') != xml.count('>'):
            raise BPMNGenerationError("Malformed XML: Unbalanced tags detected")
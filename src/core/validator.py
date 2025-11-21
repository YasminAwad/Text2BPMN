from ..exceptions import BPMNValidationError
import re

class BPMNFileValidator:
    """Validates and cleans BPMN XML content."""

    REQUIRED_ELEMENTS = ["definitions", "process", "startEvent", "endEvent"]

    # Node local names considered "graphical nodes" that should have shapes
    GRAPHICAL_NODE_LOCALNAMES = {
        "task", "userTask", "serviceTask", "scriptTask", "startEvent",
        "endEvent", "intermediateThrowEvent", "exclusiveGateway", "parallelGateway",
        "subProcess", "callActivity"
    }

    @staticmethod
    def clean_xml(xml: str) -> str:
        """
        Remove markdown code fences and extra whitespace from XML.
        """
        xml = re.sub(r'```xml\s*', '', xml)
        xml = re.sub(r'```\s*', '', xml)
        
        xml = xml.strip()
        
        return xml

    @staticmethod
    def validate(xml: str) -> None:
        """
        Validate that XML contains required BPMN elements.
        """
        if not xml:
            raise BPMNValidationError("Empty XML content")
        
        if not xml.startswith("<?xml"):
            raise BPMNValidationError(
                "Missing XML declaration. BPMN file must start with <?xml version=\"1.0\"?>"
            )
        
        for element in BPMNFileValidator.REQUIRED_ELEMENTS:
            if element not in xml:
                raise BPMNValidationError(
                    f"Missing required BPMN element: <{element}>. "
                    f"A valid BPMN diagram must contain: {', '.join(BPMNFileValidator.REQUIRED_ELEMENTS)}"
                )
        
        # Basic XML structure check
        if xml.count('<') != xml.count('>'):
            raise BPMNValidationError("Malformed XML: Unbalanced tags detected")
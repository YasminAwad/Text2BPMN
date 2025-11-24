import re
import logging

from ..exceptions import BPMNValidationError


class XMLValidator:
    """Validates and cleans BPMN XML content."""

    REQUIRED_ELEMENTS = ["definitions", "process", "startEvent", "endEvent"]

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
        
        for element in XMLValidator.REQUIRED_ELEMENTS:
            if element not in xml:
                raise BPMNValidationError(
                    f"Missing required BPMN element: <{element}>. "
                    f"A valid BPMN diagram must contain: {', '.join(XMLValidator.REQUIRED_ELEMENTS)}"
                )
        
        # Basic XML structure check
        if xml.count('<') != xml.count('>'):
            raise BPMNValidationError("Malformed XML: Unbalanced tags detected")

    @staticmethod
    def remove_file_wrapper(llm_xml: str) -> str:
        lane_xml_file_match = re.search(r"<file>(.*?)</file>", llm_xml, re.DOTALL)
        if not lane_xml_file_match:
            logging.error("The response does not contain a valid xml BPMN file.")
            raise BPMNValidationError("Failed to generate BPMN file.")
        lane_raw_xml = lane_xml_file_match.group(1).strip()
        return lane_raw_xml
    
    @staticmethod
    def validate_and_clean(xml: str) -> str:
        """
        Validate and clean BPMN XML content.
        """
        xml = XMLValidator.clean_xml(xml)
        XMLValidator.validate(xml)
        return xml
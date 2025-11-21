import re
import logging

from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from ..utils.prompt import retrieve_prompt
from .llm import LLMService
from .validator import BPMNFileValidator
from ..exceptions import BPMNGenerationError


class BPMNGeneratorService:
    def __init__(self, llm_service: LLMService):
        """Main service orchestrating BPMN generation pipeline."""
    
        self.llm_service = llm_service
        self.validator = BPMNFileValidator()

    def generate_bpmn(self, process_description: SyntaxError) -> str:
        """
        Generate BPMN XML from natural language description.
        
        Args:
            process_description: Natural language process description
            
        Returns:
            Valid BPMN 2.0 XML string
        """
        logging.info("Starting BPMN generation")

        prompt_content = retrieve_prompt("bpmn_generation_prompt.txt")
        prompt_template = ChatPromptTemplate.from_messages([
                ("system", prompt_content)
            ])
        
        response = self.llm_service.run_prompt(prompt_template, {"process_description": process_description})
        logging.debug("LLM response: %s", response)

        logging.debug("Extracting BPMN file...")
        xml_file_match = re.search(r"<file>(.*?)</file>", response, re.DOTALL)
        if not xml_file_match:
            raise BPMNGenerationError("Failed to generate BPMN file")
        raw_xml = xml_file_match.group(1).strip()

        logging.debug("Validating BPMN...")
        cleaned_xml = self.validator.clean_xml(raw_xml)
        self.validator.validate(cleaned_xml)

        reasoning_match = re.search(r"<reasoning>(.*?)</reasoning>", response, re.DOTALL)
        if not reasoning_match:
            reasoning = "Reasoning not found in response."
        else:
            reasoning = reasoning_match.group(1).strip()

        logging.info("BPMN generation complete")
        return cleaned_xml, reasoning
    
    def save_bpmn(self, bpmn_xml: str, save_path: str) -> None:
        """
        Save BPMN XML to file.
        
        Args:
            bpmn_xml: Valid BPMN XML content
            save_path: Path where to save the file
            
        Raises:
            BPMNGenerationError: If file cannot be saved
        """
        try:
            path = Path(save_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(bpmn_xml)
                
        except Exception as e:
            raise BPMNGenerationError(f"Failed to save BPMN file: {str(e)}")


import re, json
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

        prompt_content = retrieve_prompt("from_description_to_json.txt")
        logging.debug("Prompt content:\n%s", prompt_content)
        prompt_template = ChatPromptTemplate.from_messages([
                ("system", prompt_content)
            ])
        logging.debug("Prompt template:\n%s", prompt_template)
        json_content = self.llm_service.run_prompt(prompt_template, {"process_description": process_description})
        logging.debug("JSON LLM response:\n%s", json_content)

        try:
            json_loaded =json.loads(json_content)
            json_bpmn = json_loaded["bpmn"]
            reasoning = json_loaded["reasoning"]

        except (ValueError, TypeError):
            logging.error("The response is not a valid JSON object or does not contain a 'process' key.")
            raise BPMNGenerationError("Failed to generate BPMN file")
        
        json_bpmn_str = json.dumps(json_bpmn)

        prompt = retrieve_prompt("from_json_to_xml.txt")
        prompt_template = ChatPromptTemplate.from_messages([
                ("system", prompt)
            ])
        
        xml_content = self.llm_service.run_prompt(prompt_template, {"json_bpmn": json_bpmn_str})
        logging.debug("XML LLM response:\n%s", xml_content)
        xml_file_match = re.search(r"<file>(.*?)</file>", xml_content, re.DOTALL)
        if not xml_file_match:
            logging.error("The response does not contain a valid xml BPMN file.")
            raise BPMNGenerationError("Failed to generate BPMN file")
        raw_xml = xml_file_match.group(1).strip()

        logging.debug("Validating BPMN...")
        cleaned_xml = self.validator.clean_xml(raw_xml)
        self.validator.validate(cleaned_xml)

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


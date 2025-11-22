import re, json
import logging

from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from ..utils.prompt import retrieve_prompt
from .llm import LLMService
from .validator import BPMNFileValidator
from ..exceptions import BPMNGenerationError, BPMNLayoutError
from .layout import BPMNLayoutService


class BPMNGeneratorService:
    def __init__(self, llm_service: LLMService):
        """Main service orchestrating BPMN generation pipeline."""
    
        self.llm_service = llm_service
        self.validator = BPMNFileValidator()
        try:
            self.layout_service = BPMNLayoutService()
            logging.info("Auto-layout enabled")
        except BPMNLayoutError as e:
            logging.error(f"Auto-layout service initialization failed: {e}")
            raise BPMNGenerationError("Failed to generate BPMN file")


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
        logging.debug("COMPLEX JSON LLM response:\n%s", json_content)

        try:
            json_loaded =json.loads(json_content)
            json_bpmn = json_loaded["bpmn"]
            reasoning = json_loaded["reasoning"]

        except (ValueError, TypeError):
            logging.error("The response is not a valid JSON object or does not contain a 'process' key.")
            raise BPMNGenerationError("Failed to generate BPMN file")
        
        json_bpmn_str = json.dumps(json_bpmn)


        # SIMPLER JSON
            

        prompt_content = retrieve_prompt("simpler_json.txt")
        logging.debug("Prompt content:\n%s", prompt_content)
        prompt_template = ChatPromptTemplate.from_messages([
                ("system", prompt_content)
            ])
        logging.debug("Prompt template:\n%s", prompt_template)
        simpler_json_content = self.llm_service.run_prompt(prompt_template, {"original_json": json_bpmn_str})
        logging.debug("SIMPLER JSON LLM response:\n%s", json_content)

        try:
            simpler_json_loaded =json.loads(simpler_json_content)
            simpler_json_bpmn = simpler_json_loaded["bpmn"]
        except (ValueError, TypeError):
            logging.error("The response is not a valid JSON object or does not contain a 'process' key.")
            raise BPMNGenerationError("Failed to generate BPMN file")
        
        simpler_json_bpmn_str = json.dumps(simpler_json_bpmn)



        # GENERATE FIRST XML

        prompt = retrieve_prompt("from_simpler_json_to_xml.txt")
        prompt_template = ChatPromptTemplate.from_messages([
                ("system", prompt)
            ])
        
        xml_content = self.llm_service.run_prompt(prompt_template, {"json_bpmn": json_bpmn_str})
        logging.debug("FIRST XML LLM response:\n%s", xml_content)
        xml_file_match = re.search(r"<file>(.*?)</file>", xml_content, re.DOTALL)
        if not xml_file_match:
            logging.error("The response does not contain a valid xml BPMN file.")
            raise BPMNGenerationError("Failed to generate BPMN file")
        raw_xml = xml_file_match.group(1).strip()

        logging.debug("Validating BPMN...")
        cleaned_xml = self.validator.clean_xml(raw_xml)
        self.validator.validate(cleaned_xml)

        # logging.info("Applying auto-layout...")
        # try:
        #     bpmn_xml = self.layout_service.apply_layout(cleaned_xml)
        #     logging.info("Auto-layout applied successfully")
        # except BPMNLayoutError as e:
        #     logging.error(f"Auto-layout failed, using original: {e}")
        #     raise BPMNGenerationError("Failed to generate BPMN file")




        # GENERATE SECOND XML   
        prompt = retrieve_prompt("from_complex_json_to_xml.txt")
        prompt_template = ChatPromptTemplate.from_messages([
                ("system", prompt)
            ])
        
        try:
            enriched_xml_content = self.llm_service.run_prompt(prompt_template, {"original_bpmn": cleaned_xml, "simple_json": simpler_json_bpmn_str, "enriched_json": json_bpmn_str})
        except Exception as e:
            logging.error(f"Failed to run ENRICHED llm chain: {str(e)}")
            raise BPMNGenerationError("Failed to generate BPMN file")
        
        logging.debug("SECOND XML LLM response:\n%s", enriched_xml_content)
        enriched_xml_file_match = re.search(r"<file>(.*?)</file>", enriched_xml_content, re.DOTALL)
        if not enriched_xml_file_match:
            logging.error("The response does not contain a valid xml BPMN file.")
            raise BPMNGenerationError("Failed to generate BPMN file")
        enriched_raw_xml = enriched_xml_file_match.group(1).strip()

        logging.debug("Validating BPMN...")
        cleaned_xml = self.validator.clean_xml(enriched_raw_xml)
        self.validator.validate(cleaned_xml)

        self.save_bpmn(cleaned_xml, "/home/yasmin/Documents/job_search/companies/ValueBlue-Uthrecht/Text2BPMN/before_adjustment_2.bpmn")
        
        # ADJUST XML
        prompt = retrieve_prompt("adjust_graph.txt")
        prompt_template = ChatPromptTemplate.from_messages([
                ("system", prompt)
            ])
        
        try:
            enriched_xml_content = self.llm_service.run_prompt(prompt_template, {"input_xml": cleaned_xml})
        except Exception as e:
            logging.error(f"Failed to run ENRICHED llm chain: {str(e)}")
            raise BPMNGenerationError("Failed to generate BPMN file")
        
        logging.debug("SECOND XML LLM response:\n%s", enriched_xml_content)
        enriched_xml_file_match = re.search(r"<file>(.*?)</file>", enriched_xml_content, re.DOTALL)
        if not enriched_xml_file_match:
            logging.error("The response does not contain a valid xml BPMN file.")
            raise BPMNGenerationError("Failed to generate BPMN file")
        enriched_raw_xml = enriched_xml_file_match.group(1).strip()

        logging.debug("Validating BPMN...")
        cleaned_xml = self.validator.clean_xml(enriched_raw_xml)
        self.validator.validate(cleaned_xml)

        

        

        logging.info("BPMN generation complete")
        return cleaned_xml, reasoning # bpmn_xml
    
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


from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pathlib import Path

from ..config import get_model_config
from ..utils.prompt import retrieve_prompt
from ..utils.file_handler import check_directory_existace


class BPMNGenerationError(Exception):
    """Raised when BPMN generation fails."""
    pass


class BPMNGeneratorService:
    """
    Service class for generating .bpmn files from natural language.
    Encapsulates LLM interaction and BPMN generation logic.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the BPMN generator service.
        
        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key
        self.config = get_model_config()
        
        self.generation_llm = self._create_llm(self.config['temperature'])
    

    
    def generate_bpmn(self, process_description: str, prompt_file_name: str = "bpmn_generation_prompt.txt") -> str:
        """
        Generate BPMN 2.0 XML from process description.
        
        Args:
            process_description: Natural language process description
            
        Returns:
            BPMN 2.0 XML string
            
        Raises:
            BPMNGenerationError: If BPMN generation fails
        """
        try:
            print(process_description)
            prompt_content = retrieve_prompt(prompt_file_name)
            prompt = ChatPromptTemplate.from_messages([
                ("system", prompt_content)
            ])
            chain = prompt | self.generation_llm | StrOutputParser()
            
            bpmn_xml = chain.invoke({"process_description": process_description})
            print("BPMN XML:")
            print(bpmn_xml)
            
            # Clean up the output (remove any markdown artifacts)
            bpmn_xml = self._clean_xml_output(bpmn_xml)
            
            # Basic validation
            self._validate_bpmn_xml(bpmn_xml)
            
            return bpmn_xml
            
        except BPMNGenerationError:
            raise
        except Exception as e:
            raise BPMNGenerationError(f"Failed to generate BPMN: {str(e)}")
    
    def _clean_xml_output(self, xml_content: str) -> str:
        """
        Clean XML output by removing markdown artifacts and extra whitespace.
        
        Args:
            xml_content: Raw XML content from LLM
            
        Returns:
            Cleaned XML content
        """
        # Remove markdown code blocks if present
        xml_content = xml_content.replace('```xml', '').replace('```', '')
        
        # Strip leading/trailing whitespace
        xml_content = xml_content.strip()
        
        return xml_content
    
    def _validate_bpmn_xml(self, xml_content: str) -> None:
        """
        Perform basic validation on generated BPMN XML.
        
        Args:
            xml_content: BPMN XML content
            
        Raises:
            BPMNGenerationError: If validation fails
        """
        if not xml_content:
            raise BPMNGenerationError("Generated BPMN XML is empty")
        
        if not xml_content.startswith('<?xml'):
            raise BPMNGenerationError(
                "Invalid BPMN XML: missing XML declaration"
            )
        
        required_elements = ['definitions', 'process', 'startEvent', 'endEvent']
        for element in required_elements:
            if element not in xml_content:
                raise BPMNGenerationError(
                    f"Invalid BPMN XML: missing required element '{element}'"
                )
    
    def save_bpmn(self, bpmn_xml: str, save_path: str) -> None:
        try:
            check_directory_existace(save_path)

            path = Path(save_path)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(bpmn_xml)
                
        except Exception as e:
            raise BPMNGenerationError(f"Failed to save BPMN file: {str(e)}")

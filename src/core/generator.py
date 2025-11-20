from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from ..utils.prompt import retrieve_prompt
from .llm import LLMService
from .validator import BPMNFileValidator, BPMNGenerationError


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
            
        Raises:
            BPMNGenerationError: If generation or validation fails
        """
        prompt_content = retrieve_prompt("bpmn_generation_prompt.txt")
        prompt_template = ChatPromptTemplate.from_messages([
                ("system", prompt_content)
            ])
        raw_xml = self.llm_service.run_prompt(prompt_template, {"process_description": process_description})
        
        cleaned = self.validator.clean_xml(raw_xml)
        self.validator.validate(cleaned)

        return cleaned
    
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
            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(bpmn_xml)
                
        except Exception as e:
            raise BPMNGenerationError(f"Failed to save BPMN file: {str(e)}")


from langchain_core.prompts import ChatPromptTemplate
import os
    
def retrieve_prompt(file_name: str) -> ChatPromptTemplate:
    """
    Retrieve the prompt content from a file.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(base_dir, "..", "prompts", file_name)

    with open(prompt_path, "r") as f:
        prompt_content = f.read()

    return prompt_content 

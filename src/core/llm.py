from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

class LLMService:
    def __init__(self, api_key: str, config: dict):
        self.llm = ChatOpenAI(
            model=config["model"],
            api_key=api_key,
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
        )

    def run_prompt(self, prompt_template: ChatPromptTemplate, variables: dict):
        try:
            chain = prompt_template | self.llm | StrOutputParser()
            response = chain.invoke(variables)
        except Exception as e:
            raise Exception(f"Failed to run llm chain: {str(e)}")
        return response

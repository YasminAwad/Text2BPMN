import logging
from typing import Dict

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI

from ..exceptions import LLMServiceError
from ..utils.prompt import retrieve_prompt


class LLMService:
    def __init__(self, api_key: str, config: dict):
        self.llm = AzureChatOpenAI(
            model=config["model"],
            api_key=api_key,
            azure_endpoint=config["azure_endpoint"],
            api_version=config["api_version"],
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
        )

    def call_llm(self, prompt_path: str, variables: Dict) -> str:
        """
        Calls the LLM to generate a response based on the provided prompt and variables.
        """
        logging.info("Running llm chain")
        prompt_content = retrieve_prompt(prompt_path)
        prompt_template = ChatPromptTemplate.from_messages([
                ("system", prompt_content)
            ])
        try:
            chain = prompt_template | self.llm | StrOutputParser()
            response = chain.invoke(variables)
            logging.debug("LLM response:\n%s", response)
        except Exception as e:
            logging.error("Failed to run llm chain: %s", str(e))
            raise LLMServiceError(f"Failed to run llm chain: {str(e)}")
        return response

from setuptools import setup, find_packages

setup(
    name="text2bpmn",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "langchain>=1.0.8",
        "langchain-openai>=1.0.3",
        "openai>=2.8.1",
        "click>=8.3.1",
        "dotenv>=0.9.9",
    ],
    entry_points={
        "console_scripts": [
            "text2bpmn=src.cli:cli",
        ],
    },
)
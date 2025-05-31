import os

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

"""
This script initializes an OpenAI client using Azure OpenAI service.
It loads the necessary environment variables from a .env file and creates an instance of the AsyncAzureOpenAI client.
"""
# Load environment variables
load_dotenv(override=True)


langchain_openai_client = AzureChatOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    model="gpt-4.1",
)

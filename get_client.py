import os

from dotenv import load_dotenv
from openai import AsyncAzureOpenAI, AzureOpenAI

"""
This script initializes an OpenAI client using Azure OpenAI service.
It loads the necessary environment variables from a .env file and creates an instance of the AsyncAzureOpenAI client.
"""
# Load environment variables
load_dotenv(override=True)

# Create OpenAI client using Azure OpenAI
async_openai_client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)

openai_client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)

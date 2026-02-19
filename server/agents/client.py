from openai import AsyncOpenAI
from agents import set_default_openai_client
from server.config import settings

# Create OpenRouter client
openrouter_client = AsyncOpenAI(
    base_url=settings.OPENROUTER_BASE_URL,
    api_key=settings.OPENROUTER_API_KEY
)

# Set as default for OpenAI Agents SDK
set_default_openai_client(openrouter_client)

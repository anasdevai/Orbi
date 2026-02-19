from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from server.db.agent_service import (
    create_agent, get_all_agents, get_agent, update_agent, delete_agent
)
from server.config import settings
from typing import Optional
import json

router = APIRouter()

# Debug: Print when router is loaded
print("Loading agents router with models endpoint...")

# OpenRouter compatible models (examples - add more as needed)
OPENROUTER_MODELS = [
    'openai/gpt-oss-120b:free',
    'openai/gpt-4o',
    'openai/gpt-4o-mini',
    'openai/gpt-4-turbo',
    'anthropic/claude-3.5-sonnet',
    'anthropic/claude-3-opus',
    'google/gemini-pro',
    'meta-llama/llama-3.1-70b-instruct',
    'microsoft/phi-4',
    'mistralai/mistral-large',
]

class AgentCreate(BaseModel):
    name: str
    description: str
    system_prompt: str
    model: str = Field(default_factory=lambda: settings.DEFAULT_MODEL, description="OpenRouter model name")
    allowed_tools: list

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    allowed_tools: Optional[list] = None
    is_active: Optional[int] = None

@router.get('/agents')
async def list_agents():
    """Get all active agents."""
    agents = await get_all_agents()
    return agents

@router.post('/agents')
async def create_new_agent(agent: AgentCreate):
    """Create a new agent with OpenRouter-compatible model."""
    # Use default model if not specified
    model = agent.model or settings.DEFAULT_MODEL
    
    agent_id = await create_agent(
        name=agent.name,
        description=agent.description,
        system_prompt=agent.system_prompt,
        model=model,
        allowed_tools=agent.allowed_tools
    )
    return {
        'id': agent_id,
        'message': 'Agent created successfully',
        'model': model
    }

@router.get('/agents/models')
async def list_available_models():
    """Get list of available OpenRouter models."""
    return {
        'default_model': settings.DEFAULT_MODEL,
        'planner_model': settings.PLANNER_MODEL,
        'available_models': OPENROUTER_MODELS,
        'note': 'You can use any OpenRouter model. Visit https://openrouter.ai/models for the full list.'
    }

@router.get('/agents/{agent_id}')
async def get_agent_by_id(agent_id: str):
    """Get a single agent by ID."""
    agent = await get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail='Agent not found')
    return agent

@router.put('/agents/{agent_id}')
async def update_agent_by_id(agent_id: str, agent: AgentUpdate):
    """Update an agent."""
    # Check if agent exists
    existing = await get_agent(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail='Agent not found')

    # Build update dict
    update_fields = {}
    if agent.name is not None:
        update_fields['name'] = agent.name
    if agent.description is not None:
        update_fields['description'] = agent.description
    if agent.system_prompt is not None:
        update_fields['system_prompt'] = agent.system_prompt
    if agent.model is not None:
        update_fields['model'] = agent.model
    if agent.allowed_tools is not None:
        update_fields['allowed_tools'] = agent.allowed_tools
    if agent.is_active is not None:
        update_fields['is_active'] = agent.is_active

    await update_agent(agent_id, **update_fields)
    return {'message': 'Agent updated successfully'}

@router.delete('/agents/{agent_id}')
async def delete_agent_by_id(agent_id: str):
    """Soft delete an agent."""
    existing = await get_agent(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail='Agent not found')

    await delete_agent(agent_id)
    return {'message': 'Agent deleted successfully'}

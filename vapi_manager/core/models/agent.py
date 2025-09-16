from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from .assistant import Assistant
from .squad import Squad


class Agent(BaseModel):
    """
    An Agent represents a complete conversational unit containing:
    - One Squad that manages multiple assistants
    - The assistants that belong to that squad
    """
    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    squad: Squad
    assistants: List[Assistant] = Field(default_factory=list)
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")


class AgentCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    squad_name: str = Field(..., alias="squadName")
    assistant_ids: List[str] = Field(..., alias="assistantIds")


class AgentUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    squad_name: Optional[str] = Field(None, alias="squadName")
    assistant_ids: Optional[List[str]] = Field(None, alias="assistantIds")
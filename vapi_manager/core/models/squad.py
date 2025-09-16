from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class SquadMember(BaseModel):
    assistant_id: str = Field(..., alias="assistantId")
    assistant_destinations: Optional[List[Dict[str, Any]]] = Field(None, alias="assistantDestinations")


class Squad(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    org_id: Optional[str] = Field(None, alias="orgId")
    name: Optional[str] = None
    members: Optional[List[SquadMember]] = None
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")


class SquadCreateRequest(BaseModel):
    name: str
    members: List[SquadMember]


class SquadUpdateRequest(BaseModel):
    name: Optional[str] = None
    members: Optional[List[SquadMember]] = None
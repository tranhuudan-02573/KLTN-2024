from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field


class KnowledgeName(BaseModel):
    name: str = Field(..., max_length=255)


class KnowledgeCreate(KnowledgeName):
    description: Optional[str] = Field(..., max_length=1000)


class KnowledgeUpdate(KnowledgeName):
    description: Optional[str] = Field(None, max_length=1000)


class KnowledgeCreateForBot(BaseModel):
    knowledge_id: UUID


class FileIdsRequest(BaseModel):
    file_ids: List[UUID]

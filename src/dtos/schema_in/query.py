# #######################################QUERYQUERYQUERYQUERYQUERYQUERYQUERYQUERYQUERYQUERY##############################################################
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class QueryCreate(BaseModel):
    query: str


class QueryUpdate(BaseModel):
    query: str


class ConversationItem(BaseModel):
    message: str
    role: str


class ChunkPayload(BaseModel):
    page_label: str
    chunk_id: float
    file_name: str
    chunks: str
    score: float

    def to_custom_string(self) -> str:
        return (
            f"chunk {self.chunk_id} ở trang {self.page_label} của file {self.file_name} "
            f"có số điểm {self.score} với nội dung là {self.chunks}"
        )


class GeneratePayload(BaseModel):
    query_id: UUID
    query: str
    context: list[ChunkPayload]
    conversation: list[ConversationItem]

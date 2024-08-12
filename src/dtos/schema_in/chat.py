from pydantic import BaseModel
from pydantic import Field


class ChatCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)


class ChatUpdate(BaseModel):
    title: str = Field(min_length=5, max_length=200)

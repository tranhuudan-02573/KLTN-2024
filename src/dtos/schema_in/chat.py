from pydantic import BaseModel
from pydantic import Field


class ChatCreate(BaseModel):
    title: str = Field(..., max_length=200)


class ChatUpdate(BaseModel):
    title: str = Field(None, max_length=200)

# #######################################QUERYQUERYQUERYQUERYQUERYQUERYQUERYQUERYQUERYQUERY##############################################################
from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field


# #######################################BOTBOTBOTBOTBOTBOTBOT####################################################


class ChatCreate(BaseModel):
    title: str = Field(..., max_length=200)


class ChatUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)



from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class BaseOutModel(BaseModel):
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

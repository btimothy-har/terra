from datetime import datetime
from typing import Any
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict


class Session(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    timestamp: datetime
    credentials: Optional[Any] = None

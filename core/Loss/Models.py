import datetime
from enum import Enum
from typing import List, Dict, Optional
from pydantic.main import BaseModel


class LossData(BaseModel):
    problem: dict
    penalty: str
    lossData: str
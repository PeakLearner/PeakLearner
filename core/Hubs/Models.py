import datetime
from enum import Enum
from typing import List, Dict, Optional
from pydantic.main import BaseModel


class Track(BaseModel):
    categories: str
    key: str
    url: str


class HubInfo(BaseModel):
    genome: str
    isPublic: bool
    owner: str
    tracks: Dict[str, Track]



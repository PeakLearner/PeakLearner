import datetime
from enum import Enum
from typing import List, Dict, Optional
from pydantic.main import BaseModel


class Pb(str, Enum):
    peak = 'peak'
    background = 'background'


class HubModelValue(BaseModel):
    chrom: str
    chromStart: int
    chromEnd: int
    annotation: Pb
    height: float
    track: str
    penalty: str


class ModelSum(BaseModel):
    regions: int
    fp: int
    possible_fp: int
    fn: int
    possible_fn: int
    errors: int
    penalty: str
    numPeaks: int

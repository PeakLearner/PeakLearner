import datetime
from enum import Enum
from typing import List, Dict, Optional
from pydantic.main import BaseModel


class PossibleLabels(str, Enum):
    noPeak = 'noPeak'
    peakStart = 'peakStart'
    peakEnd = 'peakEnd'
    unknown = 'unknown'


class LabelValues(BaseModel):
    chrom: str
    chromStart: int
    chromEnd: int
    annotation: PossibleLabels
    createdBy: str
    lastModifiedBy: str
    lastModified: str
    track: str



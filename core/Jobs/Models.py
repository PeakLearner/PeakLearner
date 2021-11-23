import datetime
from enum import Enum
from typing import List, Dict, Optional
from pydantic.main import BaseModel


class ModelType(str, Enum):
    none = 'None'
    lopart = 'Lopart'
    flopart = 'Flopart'


class JobType(str, Enum):
    pregen = 'pregen'
    gridSearch = 'gridSearch'
    model = 'model'
    predict = 'predict'


class Status(str, Enum):
    new = 'New'
    queued = 'Queued'
    processing = 'Processing'
    done = 'Done'
    error = 'Error'
    nodata = 'NoData'


class Problem(BaseModel):
    chrom: str
    start: int
    end: int


class TaskType(str, Enum):
    model = 'model'
    feature = 'feature'


class Task(BaseModel):
    taskType: TaskType
    id: int
    status: Status
    penalty: Optional[str] = None


class TaskInfo(BaseModel):
    user: str
    hub: str
    track: str
    id: int
    problem: Problem
    url: str
    status: Status
    lastModified: Optional[datetime.datetime]
    task: Task


class Job(BaseModel):
    id: int
    user: str
    hub: str
    track: str
    problem: Problem
    url: str
    lastModified: Optional[datetime.datetime]
    tasks: List[Task]











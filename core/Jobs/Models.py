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
    chromStart: int
    chromEnd: int


class TaskType(str, Enum):
    model = 'model'
    feature = 'feature'


class Task(BaseModel):
    type: TaskType
    taskId: str
    status: Status
    penalty: Optional[str] = None


class TaskInfo(Task):
    user: str
    hub: str
    track: str
    problem: Problem
    iteration: str
    jobStatus: Status
    id: str
    trackUrl: str
    lastModified: Optional[datetime.datetime]


class Job(BaseModel):
    id: int
    jobType: JobType
    status: Status
    user: str
    hub: str
    track: str
    problem: Problem
    trackUrl: str
    priority: int
    iteration: int
    lastModified: Optional[datetime.datetime]
    tasks: Dict[str, Task]











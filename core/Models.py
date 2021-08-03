import datetime
from pydantic.main import BaseModel
from typing import List


class Tasks(BaseModel):
    type: str
    task: int
    penalty: float

    class Config:
        schema_extra = {
            'example': {
                'type': 'model',
                'taskId': 3,
                'priority': 12
            }
        }


class Job(BaseModel):
    id: int
    status: str
    user: str
    hub: str
    track: str
    problem: dict
    trackUrl: str
    priority: int
    iteration: int
    lastModified: datetime.datetime
    tasks: List[Tasks]






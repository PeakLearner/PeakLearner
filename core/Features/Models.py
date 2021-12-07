from pydantic.main import BaseModel


class FeatureData(BaseModel):
    data: str
    problem: dict
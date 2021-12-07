from pydantic import BaseModel

class User(BaseModel):
    name: str


class Hub(BaseModel):
    owner: str
    hubName: str
    genome: str
    public: bool


class Track(BaseModel):
    owner: str
    hubName: str
    trackName: str
    categories: str
    url: str
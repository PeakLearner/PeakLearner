import core
from fastapi import Response, Request, Depends
from sqlalchemy.orm import Session
from core.Prediction import Prediction


@core.otherRouter.get('/runPrediction', include_in_schema=False)
async def runPrediction(db: Session = Depends(core.get_db)):
    out = Prediction.runPrediction(db)

    if isinstance(out, Response):
        return out
    return Response(status_code=200)
import core
from fastapi import Response
from core.Prediction import Prediction


@core.otherRouter.get('/runPrediction', include_in_schema=False)
async def runPrediction():
    Prediction.runPrediction({})
    return Response(status_code=200)


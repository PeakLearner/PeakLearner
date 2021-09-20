import core
from fastapi import Response, Request
from core.Prediction import Prediction


@core.otherRouter.get('/runPrediction', include_in_schema=False)
async def runPrediction():
    Prediction.runPrediction({})
    return Response(status_code=200)


@core.otherRouter.put('/predictionRefresh')
async def putPredictionRefresh(request: Request):
    data = await request.json()
    Prediction.putPredictionRefresh(data)
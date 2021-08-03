import json

from pydantic.main import BaseModel

import core
from core.Loss import Loss

from fastapi import APIRouter, Request
from fastapi.responses import Response, HTMLResponse, RedirectResponse


class LossData(BaseModel):
    lossInfo: dict
    penalty: str
    lossData: str


@core.trackRouter.put('/loss')
async def putLoss(request: Request, user: str, hub: str, track: str, lossData: LossData):
    data = {'user': user, 'hub': hub, 'track': track, **dict(lossData)}

    if Loss.putLoss(data):
        return Response(status_code=200)

    return Response(status_code=404)


@core.trackRouter.get('/loss')
def getLoss(request: Request, user: str, hub: str, track: str, ref: str, start: int, penalty):
    # Unpacks the data into 1 dict
    data = {'user': user, 'hub': hub, 'track': track, 'ref': ref, 'start': start, 'penalty': penalty}

    out = Loss.getLoss(data)

    if out is None:
        return Response(status_code=204)

    return core.dfPotentialSeriesOut(request, out)


@core.otherRouter.get('/losses')
def getAllLosses(request: Request):
    output = Loss.getAllLosses({})

    if output is None:
        return Response(status_code=204)

    return core.dfPotentialSeriesOut(request, output)
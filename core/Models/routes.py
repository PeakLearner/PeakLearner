import json

from pydantic.main import BaseModel

import core
from core.Models import Models
from core import dfDataOut
from core.util import PLConfig as cfg

from fastapi import APIRouter, Request
from fastapi.responses import Response, HTMLResponse, RedirectResponse


@core.trackRouter.get('/models')
def getModel(request: Request,
             user: str,
             hub: str,
             track: str,
             ref: str,
             start: int,
             end: int,
             modelType: str = 'NONE',
             scale: float = None,
             visibleStart: int = None,
             visibleEnd: int = None):
    authUser = request.session.get('user')

    if authUser is None:
        authUser = 'Public'
    else:
        authUser = authUser['email']

    data = {**locals(), 'authUser': authUser}

    output = Models.getModels(data=data)

    if output is None:
        return Response(status_code=204)

    if isinstance(output, list):
        return Response(status_code=204)

    if len(output.index) < 1:
        return Response(status_code=204)

    return core.dfOut(request, output)


class ModelData(BaseModel):
    modelInfo: dict
    penalty: str
    modelData: str


@core.trackRouter.put('/models')
async def putModel(request: Request, user: str, hub: str, track: str, modelData: ModelData):
    data = {'user': user, 'hub': hub, 'track': track, **dict(modelData)}
    output = Models.putModel(data)

    if output is not None:
        return output

    return Response(status_code=404)


# ---- HUB MODELS ---- #


@core.hubRouter.get('models')
def getHubModels(request: Request,
             user: str,
             hub: str,
             track: str,
             ref: str,
             start: int,
             end: int,
             modelType: str = 'NONE',
             scale: float = None,
             visibleStart: int = None,
             visibleEnd: int = None):
    authUser = request.session.get('user')

    if authUser is None:
        authUser = 'Public'
    else:
        authUser = authUser['email']

    data = {**locals(), 'authUser': authUser}

    output = Models.getHubModels(data)

    if isinstance(output, list):
        return Response(status_code=204)

    if len(output.index) < 1:
        return Response(status_code=204)

    return output


# ---- MODEL SUMS ---- #


@core.trackRouter.get('/modelSums')
def getTrackModelSums(request: Request,
                      user: str,
                      hub: str,
                      track: str,
                      ref: str,
                      start: int,
                      end: int):
    authUser = request.session.get('user')

    if authUser is None:
        authUser = 'Public'
    else:
        authUser = authUser['email']

    data = {**locals(), 'authUser': authUser}

    output = Models.getTrackModelSummaries(data)

    if output is None:
        return Response(status_code=204)

    if isinstance(output, list):
        if len(output) != 0:
            return output
        return Response(status_code=204)

    return core.dfPotentialSeriesOut(request, output)


@core.trackRouter.get('/modelSum')
def getTrackModelSum(request: Request,
                     user: str,
                     hub: str,
                     track: str,
                     ref: str,
                     start: int):
    authUser = request.session.get('user')

    if authUser is None:
        authUser = 'Public'
    else:
        authUser = authUser['email']

    data = {**locals(), 'authUser': authUser}

    output = Models.getTrackModelSummary(data)

    if output is None:
        return Response(status_code=204)

    return core.dfPotentialSeriesOut(request, output)


@core.otherRouter.get('/modelSums')
def getAllModelSums(request: Request):

    output = Models.getAllModelSummaries({})

    if output is None:
        return Response(status_code=204)

    return core.dfPotentialSeriesOut(request, output)


if cfg.testing:
    class ModelSumData(BaseModel):
        user: str
        hub: str
        track: str
        problem: dict
        sum: str

    @core.otherRouter.put('/modelSumUpload')
    async def modelSumUploadView(request: Request,  modelSumData: ModelSumData):
        Models.modelSumUpload(dict(modelSumData))
        return Response(status_code=200)

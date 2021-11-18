import json
from typing import List

from pydantic.main import BaseModel

import core
from . import PyModels
from core.Loss.Models import LossData
from core.Models import Models, PyModels
from core.util import PLConfig as cfg
from core.Permissions import Permissions

from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session


csvResponse = {
    200: {
        "content": {"text/csv": {"description": "Gets the value as a csv"}},

    }
}


@core.trackRouter.get('/models', responses=csvResponse,
                      response_model=List[PyModels.HubModelValue],
                      summary='Get the models for a given track',
                      description='Gets the Models for a given track, with parameters for limiting the query')
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

    # output = Models.getModels(data=data)

    output = []

    if output is None:
        return Response(status_code=204)

    if isinstance(output, list):
        return Response(status_code=204)

    if len(output.index) < 1:
        return Response(status_code=204)

    return core.dfOut(request, output)





@core.trackRouter.put('/models',
                      summary='Put new PeakSegDiskModel',
                      description='Allows HPC clusters to upload the models which they create')
async def putModel(request: Request, user: str, hub: str, track: str, modelData: PyModels.ModelData, db: Session = Depends(core.get_db)):
    output = Models.putModel(db, user, hub, track, modelData)

    if output is not None:
        return output

    return Response(status_code=404)


# ---- HUB MODELS ---- #


@core.hubRouter.get('/models',
                    response_model=List[PyModels.HubModelValue],
                    responses=csvResponse,
                    summary='Get the models for a given hub',
                    description='Gets the models for a given track, with parameters for limiting the query')
def getHubModels(request: Request,
                 user: str,
                 hub: str,
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

    return core.dfOut(request, output)


# ---- MODEL SUMS ---- #


@core.trackRouter.get('/modelSums', responses=csvResponse,
                      summary='Get the model summaries for the selected contig',
                      description='Gets the model summaries for a given track, returns data in html table. Mostly used for jbrowse.')
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


@core.trackRouter.get('/modelSum',
                      response_model=List[PyModels.ModelSum],
                      responses=csvResponse,
                      summary='Get the model summary for the given contig',
                      description='Gets the model summary for a given track and contig')
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

    if output.empty:
        return Response(status_code=204)

    return core.dfPotentialSeriesOut(request, output)


@core.otherRouter.get('/recalculateModels', include_in_schema=False)
def recalculateModels(request: Request):
    authUser = request.session.get('user')

    if authUser is None:
        authUser = 'Public'
    else:
        authUser = authUser['email']

    if Permissions.hasAdmin(authUser):
        Models.recalculateModels({'authUser': authUser})


@core.otherRouter.get('/fixModelsToModelSums', include_in_schema=False)
def fixModelsToModelSums(request: Request):
    authUser = request.session.get('user')

    if authUser is None:
        authUser = 'Public'
    else:
        authUser = authUser['email']

    if Permissions.hasAdmin(authUser):
        Models.fixModelsToModelSums({'authUser': authUser})


if cfg.testing:
    class ModelSumData(BaseModel):
        user: str
        hub: str
        track: str
        problem: dict
        sum: str


    @core.otherRouter.put('/modelSumUpload', include_in_schema=False)
    async def modelSumUploadView(request: Request, modelSumData: ModelSumData):
        Models.modelSumUpload(dict(modelSumData))
        return Response(status_code=200)

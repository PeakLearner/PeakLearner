import json
from typing import Optional

from pydantic.main import BaseModel

import core
from core.Features import Features

from fastapi import APIRouter, Request
from fastapi.responses import Response, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates


class FeatureData(BaseModel):
    data: list
    problem: dict


@core.trackRouter.put('/features')
async def putFeatures(request: Request, user: str, hub: str, track: str, featureData: FeatureData):
    # Unpacks the data into 1 dict
    data = {'user': user, 'hub': hub, 'track': track, **dict(featureData)}

    if Features.putFeatures(data):
        return Response(status_code=200)

    return Response(status_code=404)


@core.trackRouter.get('/features',
                      responses={
                          200: {
                              "content": {"text/csv": {}},
                              "description": "The feature for that contig",
                          }
                      },)
def getFeatures(request: Request, user: str, hub: str, track: str, ref: str, start: int):
    # Unpacks the data into 1 dict
    data = {'user': user, 'hub': hub, 'track': track, 'ref': ref, 'start': start}

    out = Features.getFeatures(data)

    if out is None:
        return Response(status_code=204)

    return core.dfPotentialSeriesOut(request, out)


@core.otherRouter.get('/features',
                      responses={
                          200: {
                              "content": {"text/csv": {}},
                              "description": "A collection of all the features",
                          }
                      },)
def getAllFeatures(request: Request):
    out = Features.getAllFeatures({})

    if out is None:
        return Response(status_code=204)
    return core.dfPotentialSeriesOut(request, out)

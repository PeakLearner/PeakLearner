import json

from pydantic.main import BaseModel

import core
from core.Loss import Loss
from . import Models
from core import models
from sqlalchemy.orm import Session

from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response, HTMLResponse, RedirectResponse


@core.trackRouter.get('/loss',
                      summary='Get loss for a model',
                      description='Provides information on loss given a model')
def getLoss(request: Request, user: str, hub: str, track: str, ref: str, start: int, penalty):
    # Unpacks the data into 1 dict
    data = {'user': user, 'hub': hub, 'track': track, 'ref': ref, 'start': start, 'penalty': penalty}

    out = Loss.getLoss(data)

    if out is None:
        return Response(status_code=204)

    return core.dfPotentialSeriesOut(request, out)

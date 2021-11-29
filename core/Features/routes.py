import json


import core
from core.Features import Features

from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from .Models import FeatureData


@core.trackRouter.put('/features',
                      summary='Put features',
                      description='Allows HPC clusters to upload the features which they generate')
async def putFeatures(request: Request, user: str, hub: str, track: str,
                      featureData: FeatureData, db: Session = Depends(core.get_db)):
    """Saves features to the db"""
    # Unpacks the data into 1 dict
    db.commit()
    if Features.putFeatures(db, user, hub, track, featureData):
        return Response(status_code=200)

    return Response(status_code=404)


@core.trackRouter.get('/features',
                      responses={
                          200: {
                              "content": {"text/csv": {}},
                              "description": "The feature for that contig",
                          }
                      },
                      summary='Get features for current viewed track region',
                      description='Provides information on current features within a region')
def getFeatures(request: Request, user: str, hub: str, track: str, ref: str, start: int,
                db: Session = Depends(core.get_db)):
    "Retrieves a feature vec from the db for a given region"
    # Unpacks the data into 1 dict
    data = {'user': user, 'hub': hub, 'track': track, 'ref': ref, 'start': start}

    out = Features.getFeatures(data)

    if out is None:
        return Response(status_code=204)

    return core.dfPotentialSeriesOut(request, out)

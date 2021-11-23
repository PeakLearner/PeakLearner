import datetime
import json
from typing import Optional, List

import pandas as pd
from pydantic.main import BaseModel
from sqlalchemy.orm import Session

import core
from core import models, dbutil
from core.User import User
from core.Labels import Labels, Models
from core.Permissions import Permissions
from core.util.bigWigUtil import checkInBounds
from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response, HTMLResponse, RedirectResponse

csvResponse = {
    200: {
        "content": {"text/csv": {"description": "Gets the value as a csv"}},
    }
}

jbrowseMapper = {'chrom': 'ref', 'annotation': 'label'}


@core.trackRouter.get('/labels',
                      responses=csvResponse,
                      summary='Get the labels for a given track',
                      description='Gets the labels for a given track, with parameters for limiting the query')
def getLabels(request: Request, user: str, hub: str, track: str, ref: str = None, start: int = None,
              end: int = None, db: Session = Depends(core.get_db)):
    db.commit()
    output = Labels.getLabels(db, user, hub, track, ref=ref)
    db.commit()
    try:
        if not output:
            return Response(status_code=204)
    except ValueError:
        pass
    if isinstance(output, Response):
        return output

    if end is not None is not start:
        inBounds = output.apply(checkInBounds, axis=1, args=(start, end))
        output = output[inBounds].rename(jbrowseMapper, axis=1)

    if 'Accept' in request.headers:
        outputType = request.headers['Accept']
    else:
        outputType = 'application/json'

    if outputType == 'json' or outputType == 'application/json' or outputType == '*/*':
        outputDict = output.to_dict('records')
        return outputDict

    elif outputType == 'csv' or outputType == 'text/csv':
        return Response(output.to_csv(sep='\t', index=False), media_type='text/csv')
    else:
        return Response(status_code=404)


class LabelQuery(BaseModel):
    ref: str
    start: int
    end: int
    label: Optional[str] = None


@core.trackRouter.put('/labels',
                      summary='Add label for a given track',
                      description='Adds the label at the given position to the current args')
async def putLabel(request: Request, user: str, hub: str, track: str,
                   label: LabelQuery, db: Session = Depends(core.get_db)):
    authUser = User.getAuthUser(request, db)
    db.commit()
    out = Labels.putLabel(db, authUser, user, hub, track, label)

    if isinstance(out, Response):
        db.rollback()
        return out
    if out:
        db.commit()
        return out.id


@core.trackRouter.post('/labels',
                       summary='Update labels for a given track',
                       description='Updates the label at the given position to the current args')
async def postLabel(request: Request, user: str, hub: str, track: str, label: LabelQuery,
                    db: Session = Depends(core.get_db)):
    authUser = User.getAuthUser(request, db)

    out = Labels.updateLabel(db, authUser, user, hub, track, label)

    if isinstance(out, Response):
        db.rollback()
        return out
    else:
        db.commit()
        return out


@core.trackRouter.delete('/labels',
                         summary='Delete a label at this location',
                         description='Removes the label at the given position to the current args')
async def deleteLabel(request: Request, user: str, hub: str, track: str, label: LabelQuery,
                      db: Session = Depends(core.get_db)):
    authUser = User.getAuthUser(request, db)

    out = Labels.deleteLabel(db, authUser, user, hub, track, label)

    if isinstance(out, Response):
        db.rollback()
        return out
    if out:
        db.commit()
        return out.id


# ---- HUB LABELS ---- #

keysToInt = ['start', 'end']


class HubLabelData(BaseModel):
    ref: str
    start: int
    end: int
    tracks: Optional[list] = None
    name: Optional[str] = None


class HubLabelWithLabel(HubLabelData):
    label: str


@core.hubRouter.put('/labels',
                    summary='Add label for a given hub/tracks',
                    description='Adds the label at the given position to the current args')
def putHubLabel(request: Request, user: str, hub: str,
                hubLabelData: HubLabelWithLabel, db: Session = Depends(core.get_db)):

    authUser = User.getAuthUser(request, db)
    db.commit()

    tracks = hubLabelData.tracks

    if tracks is None:
        user, hub = dbutil.getHub(db, user, hub)
        if hub is None:
            return Response(status_code=404)

        tracks = hub.tracks.all()

    for track in tracks:
        db.commit()
        label = LabelQuery(ref=hubLabelData.ref, start=hubLabelData.start, end=hubLabelData.end,
                           label=hubLabelData.label)

        output = Labels.putLabel(db, authUser, user, hub, track, label)

        if isinstance(output, Response):
            db.rollback()
            return output

    db.commit()

    return Response(status_code=200)


@core.hubRouter.post('/labels',
                     summary='Update labels for a given hub/tracks',
                     description='Updates the label at the given position to the current args')
async def postHubLabel(request: Request, user: str, hub: str, hubLabelData: HubLabelWithLabel,
                       db: Session = Depends(core.get_db)):
    authUser = User.getAuthUser(request, db)
    db.commit()

    tracks = hubLabelData.tracks

    if tracks is None:
        user, hub = dbutil.getHub(db, user, hub)
        if hub is None:
            return Response(status_code=404)

        tracks = hub.tracks.all()

    for track in tracks:
        label = LabelQuery(ref=hubLabelData.ref, start=hubLabelData.start, end=hubLabelData.end,
                           label=hubLabelData.label)

        output = Labels.updateLabel(db, authUser, user, hub, track, label)

        if isinstance(output, Response):
            db.rollback()
            return output

    db.commit()

    return Response(status_code=200)


@core.hubRouter.delete('/labels',
                       summary='Delete a label at this location',
                       description='Removes the label at the given position to the current args')
async def deleteHubLabel(request: Request, user: str, hub: str, hubLabelData: HubLabelData,
                         db: Session = Depends(core.get_db)):
    authUser = User.getAuthUser(request, db)
    db.commit()

    tracks = hubLabelData.tracks

    if tracks is None:
        user, hub = dbutil.getHub(db, user, hub)
        if hub is None:
            return Response(status_code=404)

        tracks = hub.tracks.all()

    for track in tracks:
        label = LabelQuery(ref=hubLabelData.ref, start=hubLabelData.start, end=hubLabelData.end)

        Labels.deleteLabel(db, authUser, user, hub, track, label)

    db.commit()

    return Response(status_code=200)

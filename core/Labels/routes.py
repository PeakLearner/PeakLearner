import datetime
import json
from typing import Optional, List

import pandas as pd
from pydantic.main import BaseModel
from sqlalchemy.orm import Session

import core
from core import models, dbutil
from core.User import User
from core.util.bigWigUtil import checkInBounds
from core.Labels import Labels, Models
from core.Permissions import Permissions
from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response, HTMLResponse, RedirectResponse

csvResponse = {
    200: {
        "content": {"text/csv": {"description": "Gets the value as a csv"}},
    }
}


def onlyInBoundsAsDf(toCheck, start=None, end=None):
    return pd.DataFrame(onlyInBounds(toCheck, start, end))


def onlyInBounds(toCheck, start=None, end=None):
    output = []

    for checking in toCheck:
        if start and not end:
            if checking['start'] >= start:
                output.append(checking)
        elif end and not start:
            if checking['end'] <= end:
                output.append(checking)
        elif start and end:
            if start <= checking['start'] <= end:
                output.append(checking)
            elif start <= checking['end'] <= end:
                output.append(checking)
            else:
                output.append(checking)

    return output


@core.trackRouter.get('/labels',
                      responses=csvResponse,
                      summary='Get the labels for a given track',
                      description='Gets the labels for a given track, with parameters for limiting the query')
def getLabels(request: Request, user: str, hub: str, track: str, ref: str = None, start: int = None,
              end: int = None, db: Session = Depends(core.get_db)):
    user, hub, track = dbutil.getTrack(db, user, hub, track)

    if ref:
        user, hub, track, chrom = dbutil.getChrom(db, user, hub, track, ref)
        output = chrom.getLabels(queryFilter=onlyInBoundsAsDf, start=start, end=end)
    else:
        output = track.getLabels(start=start, end=end)

    try:
        if not output:
            return Response(status_code=204)
    except ValueError:
        pass
    if isinstance(output, Response):
        return output

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

    user, hub = dbutil.getHub(db, user, hub)

    if not hub.checkPermission(authUser, 'Label'):
        if authUser.name == 'Public':
            return Response(status_code=401)
        return Response(status_code=403)

    user, hub, track, chrom = dbutil.getChrom(db, user, hub, track, label.ref)

    labelsDf = pd.DataFrame(chrom.getLabels())

    inBounds = labelsDf.apply(checkInBounds, axis=1, args=(label.start, label.end))

    if inBounds.any():
        return Response(status_code=406)

    newLabel = models.Label(chrom=chrom.id,
                            annotation=label.label,
                            start=label.start,
                            end=label.end,
                            lastModified=datetime.datetime.now(),
                            lastModifiedBy=authUser.id)

    chrom.labels.append(newLabel)
    db.commit()

    return Response(status_code=200)


@core.trackRouter.post('/labels',
                       summary='Update labels for a given track',
                       description='Updates the label at the given position to the current args')
async def postLabel(request: Request, user: str, hub: str, track: str, label: LabelQuery):
    authUser = request.session.get('user')

    if authUser is None:
        authUser = 'Public'
    else:
        authUser = authUser['email']

    query = {'user': user, 'hub': hub, 'track': track, 'authUser': authUser, **dict(label)}

    out = Labels.updateLabel(query)

    if isinstance(out, Response):
        return out

    return out


@core.trackRouter.delete('/labels',
                         summary='Delete a label at this location',
                         description='Removes the label at the given position to the current args')
async def deleteLabel(request: Request, user: str, hub: str, track: str, label: LabelQuery):
    authUser = request.session.get('user')

    if authUser is None:
        authUser = 'Public'
    else:
        authUser = authUser['email']

    query = {'user': user, 'hub': hub, 'track': track, 'authUser': authUser, **dict(label)}

    out = Labels.deleteLabel(query)

    if isinstance(out, Response):
        return out
    if out:
        return Response(status_code=200)
    return Response(status_code=404)


# ---- HUB LABELS ---- #

keysToInt = ['start', 'end']


@core.hubRouter.get('/labels',
                    response_model=List[Models.LabelValues],
                    responses=csvResponse,
                    summary='Get the labels for a given hub/tracks',
                    description='Gets the labels for a given track, with parameters for limiting the query')
async def getHubLabels(request: Request, user: str, hub: str, contig: bool = False):
    authUser = request.session.get('user')

    if authUser is None:
        authUser = 'Public'
    else:
        authUser = authUser['email']
    data = {'user': user, 'hub': hub, 'authUser': authUser, 'contig': contig}

    output = Labels.getHubLabels(data)

    if isinstance(output, list):
        return Response(status_code=204)
    elif isinstance(output, Response):
        return output

    return core.dfOut(request, output)


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
async def putHubLabel(request: Request, user: str, hub: str, hubLabelData: HubLabelWithLabel):
    authUser = request.session.get('user')

    if authUser is None:
        authUser = 'Public'
    else:
        authUser = authUser['email']
    data = {'user': user, 'hub': hub, **dict(hubLabelData), 'authUser': authUser}

    output = Labels.addHubLabels(data)

    if isinstance(output, Response):
        return output

    return Response(json.dumps(output), media_type='application/json')


@core.hubRouter.post('/labels',
                     summary='Update labels for a given hub/tracks',
                     description='Updates the label at the given position to the current args')
async def postHubLabel(request: Request, user: str, hub: str, hubLabelData: HubLabelWithLabel):
    authUser = request.session.get('user')

    if authUser is None:
        authUser = 'Public'
    else:
        authUser = authUser['email']
    data = {'user': user, 'hub': hub, **dict(hubLabelData), 'authUser': authUser}

    output = Labels.updateHubLabels(data)

    if isinstance(output, Response):
        return output

    return Response(json.dumps(output), media_type='application/json')


@core.hubRouter.delete('/labels',
                       summary='Delete a label at this location',
                       description='Removes the label at the given position to the current args')
async def deleteHubLabel(request: Request, user: str, hub: str, hubLabelData: HubLabelData):
    authUser = request.session.get('user')

    if authUser is None:
        authUser = 'Public'
    else:
        authUser = authUser['email']
    data = {'user': user, 'hub': hub, **dict(hubLabelData), 'authUser': authUser}

    output = Labels.deleteHubLabels(data)

    if isinstance(output, Response):
        return output

    return Response(json.dumps(output), media_type='application/json')

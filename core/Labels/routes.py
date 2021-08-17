import json
from typing import Optional, List

from pydantic.main import BaseModel

import core
from core.Labels import Labels, Models
from fastapi import APIRouter, Request
from fastapi.responses import Response, HTMLResponse, RedirectResponse

csvResponse = {
    200: {
        "content": {"text/csv": {"description": "Gets the value as a csv"}},
    }
}


@core.trackRouter.get('/labels',
                      responses=csvResponse,
                      summary='Get the labels for a given track',
                      description='Gets the labels for a given track, with parameters for limiting the query')
async def getLabels(request: Request, user: str, hub: str, track: str, ref: str = None, start: int = None,
                    end: int = None):
    query = {'user': user, 'hub': hub, 'track': track, 'ref': ref, 'start': start, 'end': end}
    output = Labels.getLabels(data=query)

    if isinstance(output, list):
        return Response(status_code=204)

    if 'Accept' in request.headers:
        outputType = request.headers['Accept']
    else:
        outputType = 'application/json'

    if outputType == 'json' or outputType == 'application/json' or outputType == '*/*':
        outputDict = output.to_dict('records')
        print('here')
        print(outputDict)
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
async def putLabel(request: Request, user: str, hub: str, track: str, label: LabelQuery):
    authUser = request.session.get('user')

    if authUser is None:
        authUser = 'Public'
    else:
        authUser = authUser['email']

    query = {'user': user, 'hub': hub, 'track': track, 'authUser': authUser, **dict(label)}

    return Labels.addLabel(query)


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

    return Labels.updateLabel(query)


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

    if Labels.deleteLabel(query):
        return Response(status_code=200)
    return Response(status_code=404)


# ---- HUB LABELS ---- #

keysToInt = ['start', 'end']


@core.hubRouter.get('/labels',
                    response_model=List[Models.LabelValues],
                    responses=csvResponse,
                    summary='Get the labels for a given hub/tracks',
                    description='Gets the labels for a given track, with parameters for limiting the query')
async def getHubLabels(request: Request, user: str, hub: str):
    authUser = request.session.get('user')

    if authUser is None:
        authUser = 'Public'
    else:
        authUser = authUser['email']
    data = {'user': user, 'hub': hub, 'authUser': authUser}

    output = Labels.getHubLabels(data)

    if isinstance(output, list):
        return Response(status_code=204)

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

    return Response(json.dumps(output), media_type='application/json')

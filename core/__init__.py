import json

import pandas as pd

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


otherRouter = APIRouter(
    prefix='',
    tags=['Other'],
)


userRouter = APIRouter(
    prefix='/{user}',
    tags=['User'],
    responses={404: {'description': 'Not Found'}},
)

hubRouter = APIRouter(
    prefix='/{user}/{hub}',
    tags=['Hubs'],
    responses={404: {'description': 'Not Found'}},
)

jbrowseTemplates = Jinja2Templates(directory='jbrowse/jbrowse')


trackRouter = APIRouter(
    prefix='/{user}/{hub}/{track}',
    tags=['Tracks'],
    responses={404: {'description': 'Not Found'}},
)


def dfOut(request: Request, out: pd.DataFrame):
    if 'Accept' in request.headers:
        outputType = request.headers['Accept']
    else:
        outputType = 'application/json'

    if isinstance(out, Response):
        return out

    if outputType is None:
        authUser = request.session.get('user')

        if authUser is None:
            authUser = 'Public'
        else:
            authUser = authUser['email']

        out = {'user': authUser}
        return out

    if outputType == 'json' or outputType == 'application/json' or outputType == '*/*':
        outputDict = out.to_dict('records')
        return Response(json.dumps(outputDict), media_type='application/json')

    elif outputType == 'csv' or outputType == 'text/csv':
        return Response(out.to_csv(sep='\t', index=False), media_type='text/csv')
    else:
        return Response(status_code=404)


def dfPotentialSeriesOut(request: Request, out: pd.DataFrame) -> Response:
    if 'accept' in request.headers:
        outputType = request.headers['accept']
    else:
        outputType = 'json'

    if outputType == 'json' or outputType == 'application/json' or outputType == '*/*':
        if isinstance(out, pd.Series):
            output = out.to_dict()
        else:
            output = out.to_dict('records')
        if isinstance(output, list):
            if len(output) == 1:
                output = output[0]
        return Response(json.dumps(output), media_type='application/json')
    elif outputType == 'text/csv':
        return Response(out.to_csv(), media_type='text/csv')


@otherRouter.get('/backup')
def doBackup():
    from core.util import PLdb as db
    db.cleanLogs()
    db.doBackup()

from . import Jobs

from core.util import PLConfig as cfg

from fastapi import APIRouter, Request
from fastapi.responses import Response, HTMLResponse
from fastapi.templating import Jinja2Templates

import core

router = APIRouter(
    prefix='/Jobs',
    tags=['Jobs'],
    responses={404: {'description': 'Not Found'}},
)

templates = Jinja2Templates(directory='website/templates')


@router.get('/')
async def getJobs(request: Request):
    if 'accept' in request.headers:
        outputType = request.headers['accept']
    else:
        outputType = 'json'

    if 'text/html' in outputType or outputType == '*/*':
        out = Jobs.jobsStats({})
        out['request'] = request
        return templates.TemplateResponse('stats/jobs.html', out)
    elif outputType == 'json' or outputType == 'application/json':
        return Jobs.getAllJobs({})


@router.get('/queue')
async def queueNextTask():
    # TODO: Some sort of authentication system
    out = Jobs.queueNextTask({})

    if out is None:
        return Response(status_code=204)
    return out


@router.get('/{job_id}')
async def getJobWithId(request: Request, job_id: int):
    if 'accept' in request.headers:
        outputType = request.headers['accept']
    else:
        outputType = 'json'

    data = {'jobId': job_id}
    out = Jobs.getJobWithId(data)

    if 'text/html' in outputType or outputType == '*/*':
        out['request'] = request
        return templates.TemplateResponse('stats/job.html', out)
    elif outputType == 'json' or outputType == 'application/json':
        return out


@router.post('/{job_id}')
async def postJobWithId(job_id: int, task: dict):
    data = {'id': job_id, 'task': task}

    return Jobs.updateTask(data)


@router.post('/{job_id}/reset')
async def resetJob(job_id: int):
    data = {'jobId': job_id}

    return Jobs.resetJob(data)


@router.post('/{job_id}/restart')
async def restartJob(job_id: int):
    data = {'jobId': job_id}

    output = Jobs.restartJob(data)

    return output.__dict__()


@core.trackRouter.get('/jobs')
async def getTrackJobs(user: str, hub: str, track: str, ref: str, start: int, end: int):
    data = {'user': user,
            'hub': hub,
            'track': track,
            'ref': ref,
            'start': start,
            'end': end}

    output = Jobs.getTrackJobs(data)

    return output


if cfg.testing:
    @core.otherRouter.get('/runJobSpawn')
    async def runJobSpawn():
        return Jobs.spawnJobs({})

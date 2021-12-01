from typing import List

from . import Jobs, Models

from core.util import PLConfig as cfg
from core import Authentication

from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import core

router = APIRouter(
    prefix='/Jobs',
    tags=['Jobs'],
    responses={404: {'description': 'Not Found'}},
)

templates = Jinja2Templates(directory='website/templates')


@router.get('',
            responses={
                200: {
                    "content": {"text/html": {}},
                    "description": "Gets all the jobs currently on the server",
                }
            },
            response_model=List[Models.Job],
            summary='Gets all the jobs',
            description='Gets all the jobs currently on the server')
async def getJobs(request: Request,
                  db: Session = Depends(core.get_db)):
    """Retrieves all jobs from PeakLearner"""
    if 'accept' in request.headers:
        outputType = request.headers['accept']
    else:
        outputType = 'json'

    if 'text/html' in outputType or outputType == '*/*':
        out = Jobs.jobsStats(db)
        out['request'] = request
        return templates.TemplateResponse('stats/jobs.html', out)
    elif outputType == 'json' or outputType == 'application/json':
        return Jobs.getAllJobs(db)


@router.get('/queue',
            responses={
                204: {
                    "description": "No Jobs available to queue"
                }
            },
            response_model=Models.TaskInfo,
            summary='Gets the next available task and queues it',
            description='If there is a task in a job which is able to be queued, queue it and return the job')
async def queueNextTask(db: Session = Depends(core.get_db)):
    """Queues the next job and returns the job which was queued"""
    # TODO: Some sort of authentication system
    db.commit()
    out = Jobs.queueNextTask(db)

    if out is None:
        return Response(status_code=204)
    return out


@router.get('/{job_id}/{task_id}',
            response_model=Models.TaskInfo,
            summary='Gets a task with job info',
            description='If there is a task, return the task with added job info')
async def getTask(job_id: int, task_id: int, db: Session = Depends(core.get_db)):
    """Gets a task with job info"""
    # TODO: Some sort of authentication system
    db.commit()
    out = Jobs.getTask(db, task_id)

    if out is None:
        return Response(status_code=204)
    return out


@router.get('/{job_id}',
            responses={
                200: {
                    "content": {"text/html": {}},
                    "description": "Provides information on a job",
                }
            },
            response_model=Models.Job,
            summary='Gets the job with the ID',
            description='Retrieves a job given the ID in the url')
async def getJobWithId(request: Request, job_id: int,
                  db: Session = Depends(core.get_db)):
    """Retrieves a singular job"""
    if 'accept' in request.headers:
        outputType = request.headers['accept']
    else:
        outputType = 'json'

    out = Jobs.getJobWithId(db, job_id)

    if isinstance(out, Response):
        return out

    if 'text/html' in outputType or outputType == '*/*':
        out['request'] = request
        return templates.TemplateResponse('stats/job.html', out)
    elif outputType == 'json' or outputType == 'application/json':
        return out


# Could probably be moved to a '/{job_id}/{task_id}/'
@router.post('/{job_id}', response_model=Models.TaskInfo,
             summary='Updates a task in a job',
             description='Updates the task given the parameters')
async def postJobWithId(job_id: int, task: dict, db: Session = Depends(core.get_db)):
    """Modifies a task in a job"""


    db.commit()
    out = Jobs.updateTask(db, job_id, task)
    db.commit()

    if isinstance(out, Response):
        return out


@router.post('/{job_id}/reset', response_model=Models.Job,
             summary='Resets the job',
             description='Resets the given job')
async def resetJob(job_id: int, db: Session = Depends(core.get_db)):
    """Resets all tasks which are not done"""
    return Jobs.resetJob(db, job_id)


@router.post('/{job_id}/restart', response_model=Models.Job,
             summary='Restarts the job',
             description='Restarts the given job, sets all tasks back to status New')
async def restartJob(job_id: int, db: Session = Depends(core.get_db)):
    """Completely restarts a job like it was fresh"""
    db.commit()
    out = Jobs.restartJob(db, job_id)
    db.commit()
    return out


@core.trackRouter.get('/jobs',
                      responses={
                          200: {
                              "description": "Provides the jobs",
                          }
                      },
                      summary='Get jobs for current viewed track region',
                      description='Provides information on current jobs within a region')
async def getTrackJobs(user: str, hub: str, track: str, ref: str, start: int, end: int, db: Session = Depends(core.get_db)):
    """Retrieves jobs for a given track/contig"""
    data = {'user': user,
            'hub': hub,
            'track': track,
            'ref': ref,
            'start': start,
            'end': end}

    output = Jobs.getTrackJobs(db, user, hub, track, ref, start, end)

    return output


@core.otherRouter.get('/runJobSpawn', include_in_schema=False)
async def runJobSpawn():
    """Checks to see if jobs can be spawned, if so then it spawns them"""
    return Jobs.spawnJobs({})


@core.otherRouter.get('/checkRestartJobs', include_in_schema=False)
async def checkRestartJobs(db: Session = Depends(core.get_db)):
    """Checks if a job hasn't been modified in more than an hour, if so then restart the job"""
    db.commit()
    Jobs.checkRestartJobs(db)
    db.commit()

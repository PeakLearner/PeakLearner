import json
from core.Jobs import Jobs
from pyramid.view import view_config
from pyramid.response import Response

try:
    import uwsgi
    import uwsgidecorators

    @uwsgidecorators.timer(300, target='mule')
    def start_lock_detect(num):
        Jobs.checkRestartJobs({})


except ModuleNotFoundError:
    loadLater = True
    print('Running in non uwsgi mode, jobs won\'t be automatically restarted')


def jobOutput(func):

    def wrap(request):
        outputType = None

        if 'Accept' in request.headers:
            outputType = request.headers['Accept']

        output = func(request)

        if 'text/html' in outputType:
            output['user'] = request.authenticated_userid
            return output
        elif outputType == 'json' or outputType == 'application/json':
            return Response(json.dumps(output), charset='utf8', content_type='application/json')
        else:
            return Response(status=404)

    return wrap


@view_config(route_name='jobs', request_method='GET', renderer='website:stats/jobs.html')
@jobOutput
def getJobs(request):
    return Jobs.stats()


@view_config(route_name='jobQueue', request_method='GET')
def queueNextTask(request):
    # TODO: Some sort of authentication system
    task = Jobs.queueNextTask({})
    if task is None:
        return Response(status=404)
    else:
        return Response(json.dumps(task), charset='utf8', content_type='application/json')


@view_config(route_name='jobsWithId', request_method='GET', renderer='website:stats/job.html')
@jobOutput
def getJobWithId(request):
    data = {'jobId': request.matchdict['jobId']}
    return Jobs.getJobWithId(data)


@view_config(route_name='jobsWithId', request_method='POST', renderer='json')
def postJobWithId(request):
    data = {'id': request.matchdict['jobId'], 'task': request.json_body}

    return Jobs.updateTask(data)


@view_config(route_name='resetJob', request_method='POST', renderer='json')
def resetJob(request):
    data = {'jobId': request.matchdict['jobId']}

    return Jobs.resetJob(data)


@view_config(route_name='restartJob', request_method='POST', renderer='json')
def restartJob(request):
    data = {'jobId': request.matchdict['jobId']}

    output = Jobs.restartJob(data)

    if output is None:
        return Response(status=404)

    return output.__dict__()

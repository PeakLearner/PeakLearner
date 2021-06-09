import json
from core.Jobs import Jobs
from pyramid.view import view_config
from pyramid.response import Response


@view_config(route_name='jobs', request_method='GET', renderer='website:stats/jobs.html')
def getJobs(request):

    if 'outputType' in request.params:
        outputType = request.params['outputType']
    else:
        outputType = None

    output = Jobs.stats()

    if outputType is None:
        output['user'] = request.authenticated_userid
        return output

    elif outputType == 'json':
        return Response(json.dumps(output), charset='utf8', content_type='application/json')


@view_config(route_name='jobQueue', request_method='GET')
def queueNextTask(request):
    print('queueNextTask')
    # TODO: Some sort of authentication system
    task = Jobs.queueNextTask({})
    if task is None:
        return Response(status=404)
    else:
        return Response(json.dumps(task), charset='utf8', content_type='application/json')


@view_config(route_name='jobsWithId', request_method='GET', renderer='website:stats/job.html')
def getJobWithId(request):
    data = {'jobId': request.matchdict['jobId']}
    output = Jobs.getJobWithId(data)

    if 'type' in request.params:
        outputType = request.params['type']
    else:
        output['user'] = request.authenticated_userid
        return output

    if outputType == 'json':
        return Response(json.dumps(output), charset='utf8', content_type='application/json')


@view_config(route_name='jobsWithId', request_method='POST')
def postJobWithId(request):
    print('postJob')

    data = {'id': request.matchdict['jobId'], 'task': request.json_body}

    output = Jobs.updateTask(data)

    return Response(json.dumps(output), charset='utf8', content_type='application/json')


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

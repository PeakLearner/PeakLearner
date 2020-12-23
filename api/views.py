from pyramid.view import view_config
from api.Handlers import Jobs, Hubs


@view_config(route_name='jobInfo', renderer='json')
def jobStatus(request):
    return Jobs.getAllJobs({})


@view_config(route_name='jobs', renderer='json')
def jobs(request):
    query = request.matchdict
    if 'GET' == request.method:
        return Jobs.getAllJobs({})
    if 'POST' == request.method:
        return Jobs.JobHandler(query).runCommand(request.method, request.json_body)
    return []


@view_config(route_name='uploadHubUrl', renderer='json')
def uploadHubUrl(request):
    if 'POST' == request.method:
        # TODO: Implement user authentication (and maybe an anonymous user?)
        return Hubs.parseHub({'user': 1, 'url': request.json_body['args']['hubUrl']})
    return


@view_config(route_name='hubInfo', renderer='json')
def hubInfo(request):
    query = request.matchdict
    return Hubs.getHubInfo(query['user'], query['hub'])




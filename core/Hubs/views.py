import json
from core.Hubs import Hubs
from pyramid.view import view_config
from pyramid.response import Response


@view_config(route_name='hubInfo', request_method='GET')
def getHubInfo(request):
    """TODO: Document this view"""
    query = request.matchdict
    output = Hubs.getHubInfo(query['user'], query['hub'])

    return Response(json.dumps(output), charset='utf8', content_type='application/json')


@view_config(route_name='jbrowseJson', request_method='GET')
def getJbrowseJsons(request):
    query = request.matchdict
    query['currentUser'] = request.authenticated_userid
    method = request.method

    if 'json' in query['handler']:
        data = {'command': 'getJson', 'args': {'file': query['handler']}}
        query['handler'] = 'getJson'
        output = json.dumps(Hubs.HubHandler(query).runCommand(method, data))
        return Response(output,
                        charset='utf8', content_type='application/json')
    else:
        print(query['handler'], 'not yet implemented')
        return Response(status=404)

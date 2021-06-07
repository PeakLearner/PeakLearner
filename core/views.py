import json

from pyramid.view import view_config
from pyramid.response import Response
from core.Handlers import Hubs, Labels, Models


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


# ---- LABELS ---- #


@view_config(route_name='trackLabels', request_method='GET')
def getLabels(request):
    query = request.matchdict
    query['ref'] = request.params['ref']
    query['start'] = int(request.params['start'])
    query['end'] = int(request.params['end'])
    query['currentUser'] = request.authenticated_userid
    outputType = request.params['type']

    output = Labels.getLabels(data=query)

    if isinstance(output, list):
        return Response(status=204)

    if outputType == 'json' or outputType == 'application/json':
        outputDict = output.to_dict('records')
        return Response(json.dumps(outputDict), charset='utf8', content_type='application/json')

    return Response(status=404)


@view_config(route_name='trackLabels', request_method='PUT')
def putLabel(request):
    print('putLabels')
    return Response(status=404)


@view_config(route_name='trackLabels', request_method='POST')
def postLabel(request):
    print('postLabels')
    return Response(status=404)


@view_config(route_name='trackLabels', request_method='DELETE')
def deleteLabel(request):
    print('deleteLabels')
    return Response(status=404)


# ---- HUB LABELS ---- #


@view_config(route_name='hubLabels', request_method='GET')
def getHubLabels(request):
    query = request.matchdict
    if 'ref' in request.params:
        query['ref'] = request.params['ref']

    if 'start' in request.params:
        query['start'] = int(request.params['start'])

    if 'end' in request.params:
        query['end'] = int(request.params['end'])

    if 'tracks' in request.params:
        query['tracks'] = request.params['tracks'].split(',')

    query['currentUser'] = request.authenticated_userid
    outputType = request.params['type']

    output = Labels.getHubLabels(data=query)

    if output is None:
        return Response(status=404)

    if isinstance(output, list):
        return Response(status=204)

    if outputType == 'json' or outputType == 'application/json':
        outputDict = output.to_dict('records')
        return Response(json.dumps(outputDict), charset='utf8', content_type='application/json')

    return Response(status=404)


def generateHubQuery(func):
    # Handles loading the query value for hub based commands
    def wrap(request):
        query = request.matchdict
        query['ref'] = request.params['ref']
        query['start'] = int(request.params['start'])
        query['end'] = int(request.params['end'])
        if 'label' in request.params:
            query['label'] = request.params['label']
        query['currentUser'] = request.authenticated_userid

        if 'tracks' in request.params:
            query['tracks'] = request.params.getall('tracks')

        return func(query)

    return wrap


@view_config(route_name='hubLabels', request_method='PUT')
@generateHubQuery
def putHubLabel(query):
    output = Labels.addHubLabels(query)

    return Response(json.dumps(output), charset='utf8', content_type='application/json')


@view_config(route_name='hubLabels', request_method='POST')
@generateHubQuery
def postHubLabel(query):
    output = Labels.updateHubLabels(query)

    return Response(json.dumps(output), charset='utf8', content_type='application/json')


@view_config(route_name='hubLabels', request_method='DELETE')
@generateHubQuery
def deleteHubLabel(query):
    output = Labels.deleteHubLabels(query)

    return Response(json.dumps(output), charset='utf8', content_type='application/json')


# ---- MODELS ---- #


@view_config(route_name='trackModels', request_method='GET')
def getModel(request):
    query = request.matchdict
    query['ref'] = request.params['ref']
    query['start'] = int(request.params['start'])
    query['end'] = int(request.params['end'])
    query['currentUser'] = request.authenticated_userid
    query['modelType'] = request.params['modelType']
    query['scale'] = float(request.params['scale'])
    query['visibleStart'] = int(request.params['visibleStart'])
    query['visibleEnd'] = int(request.params['visibleEnd'])
    outputType = request.params['type']

    output = Models.getModels(data=query)

    if isinstance(output, list):
        return Response(status=204)

    if len(output.index) < 1:
        return Response(status=204)

    if outputType == 'json' or outputType == 'application/json':
        outputDict = json.dumps(output.to_dict('records'))
        return Response(outputDict, charset='utf8', content_type='application/json')

    return Response(status=404)


@view_config(route_name='trackModels', request_method='PUT')
def putModel(request):
    return Response(status=404)

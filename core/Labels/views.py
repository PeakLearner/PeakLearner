import json

from pyramid.view import view_config
from pyramid.response import Response
from core.Labels import Labels


def generateTrackQuery(func):
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
            query['track'] = request.params['track']

        return func(request, query)

    return wrap


@view_config(route_name='trackLabels', request_method='GET')
@generateTrackQuery
def getLabels(request, query):
    outputType = request.params['type']

    output = Labels.getLabels(data=query)

    if isinstance(output, list):
        return Response(status=204)

    if outputType == 'json' or outputType == 'application/json':
        outputDict = output.to_dict('records')
        return Response(json.dumps(outputDict), charset='utf8', content_type='application/json')

    return Response(status=404)


@view_config(route_name='trackLabels', request_method='PUT')
@generateTrackQuery
def putLabel(request, query):
    output = Labels.addLabel(query)

    return Response(json.dumps(output), charset='utf8', content_type='application/json')


@view_config(route_name='trackLabels', request_method='POST')
@generateTrackQuery
def postLabel(request, query):
    output = Labels.updateLabel(query)

    return Response(json.dumps(output), charset='utf8', content_type='application/json')


@view_config(route_name='trackLabels', request_method='DELETE')
@generateTrackQuery
def deleteLabel(request, query):
    output = Labels.deleteLabel(query)

    return Response(json.dumps(output), charset='utf8', content_type='application/json')


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
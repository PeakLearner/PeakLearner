import json
from core import dfDataOut
from core.Labels import Labels
from pyramid.view import view_config
from pyramid.response import Response


def generateTrackQuery(func):
    # Handles loading the query value for hub based commands
    def wrap(request):

        query = {**request.matchdict, **request.params}

        try:
            query = {**query, **request.json_body}
        except json.decoder.JSONDecodeError:
            pass

        try:
            query['ref'] = request.params['ref']
            query['start'] = int(request.params['start'])
            query['end'] = int(request.params['end'])
        except KeyError:
            query['ref'] = request.json_body['ref']
            query['start'] = int(request.json_body['start'])
            query['end'] = int(request.json_body['end'])

        if 'label' in request.params:
            query['label'] = request.params['label']
        query['currentUser'] = request.authenticated_userid

        if 'tracks' in request.params:
            query['track'] = request.params['track']

        return func(request, query)

    return wrap


@view_config(route_name='trackLabels', request_method='GET')
@dfDataOut
@generateTrackQuery
def getLabels(request, query):
    output = Labels.getLabels(data=query)

    if isinstance(output, list):
        return Response(status=204)

    return output


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

keysToInt = ['start', 'end']


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


@view_config(route_name='hubLabels', request_method='GET')
@dfDataOut
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

    output = Labels.getHubLabels(data=query)

    if isinstance(output, list):
        return Response(status=204)

    return output


def jsonInputWrap(func):
    # Handles loading the query value for hub based commands
    def wrap(request):
        query = {**request.matchdict, **request.json_body, 'currentUser': request.authenticated_userid}

        return func(query)

    return wrap

@view_config(route_name='hubLabels', request_method='PUT')
@jsonInputWrap
def putHubLabel(query):
    output = Labels.addHubLabels(query)

    return Response(json.dumps(output), charset='utf8', content_type='application/json')


@view_config(route_name='hubLabels', request_method='POST')
@jsonInputWrap
def postHubLabel(query):
    output = Labels.updateHubLabels(query)

    return Response(json.dumps(output), charset='utf8', content_type='application/json')


@view_config(route_name='hubLabels', request_method='DELETE')
@jsonInputWrap
def deleteHubLabel(query):
    output = Labels.deleteHubLabels(query)

    return Response(json.dumps(output), charset='utf8', content_type='application/json')
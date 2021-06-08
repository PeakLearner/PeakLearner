import json
from core.Models import Models
from pyramid.view import view_config
from pyramid.response import Response


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


# ---- HUB MODELS ---- #


@view_config(route_name='hubModels', request_method='GET')
def getHubModels(request):
    return Response(status=404)
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

    # Only really needed when generating alternative models
    try:
        query['scale'] = float(request.params['scale'])
        query['visibleStart'] = int(request.params['visibleStart'])
        query['visibleEnd'] = int(request.params['visibleEnd'])
    except KeyError:
        pass
    outputType = request.params['type']

    output = Models.getModels(data=query)

    if isinstance(output, list):
        return Response(status=204)

    if len(output.index) < 1:
        return Response(status=204)

    if outputType == 'json' or outputType == 'application/json':
        outputDict = json.dumps(output.to_dict('records'))
        return Response(outputDict, charset='utf8', content_type='application/json')
    elif outputType == 'csv' or outputType == 'text/csv':
        return Response(output.to_csv(sep='\t', index=False), charset='utf8', content_type='text/csv')

    return Response(status=404)


@view_config(route_name='trackModels', request_method='PUT', renderer='json')
def putModel(request):
    data = {**request.matchdict, **request.json_body}
    output = Models.putModel(data)

    if output is not None:
        return output


# ---- HUB MODELS ---- #


@view_config(route_name='hubModels', request_method='GET')
def getHubModels(request):
    return Response(status=404)
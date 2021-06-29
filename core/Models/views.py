import json
from core.Models import Models
from core import dfDataOut
from pyramid.view import view_config
from pyramid.response import Response
from core.util import PLConfig as cfg


@view_config(route_name='trackModels', request_method='GET')
@dfDataOut
def getModel(request):
    query = request.matchdict
    query['ref'] = request.params['ref']
    query['start'] = int(request.params['start'])
    query['end'] = int(request.params['end'])
    query['currentUser'] = request.authenticated_userid
    try:
        query['modelType'] = request.params['modelType']
    except KeyError:
        query['modelType'] = 'NONE'

    # Only really needed when generating alternative models
    try:
        query['scale'] = float(request.params['scale'])
        query['visibleStart'] = int(request.params['visibleStart'])
        query['visibleEnd'] = int(request.params['visibleEnd'])
    except KeyError:
        pass

    output = Models.getModels(data=query)

    if isinstance(output, list):
        return Response(status=204)

    if len(output.index) < 1:
        return Response(status=204)

    return output


@view_config(route_name='trackModels', request_method='PUT', renderer='json')
def putModel(request):
    data = {**request.matchdict, **request.json_body}
    output = Models.putModel(data)

    if output is not None:
        return output

    return Response(status=404)


# ---- HUB MODELS ---- #


@view_config(route_name='hubModels', request_method='GET')
@dfDataOut
def getHubModels(request):
    query = request.matchdict
    try:
        query['ref'] = request.params['ref']
        query['start'] = int(request.params['start'])
        query['end'] = int(request.params['end'])
    except KeyError:
        pass
    query['currentUser'] = request.authenticated_userid

    output = Models.getHubModels(query)

    if isinstance(output, list):
        return Response(status=204)

    if len(output.index) < 1:
        return Response(status=204)

    return output


# ---- MODEL SUMS ---- #


@view_config(route_name='trackModelSums', request_method='GET', renderer='json')
def getTrackModelSums(request):
    data = {**request.matchdict, **request.params}
    data['start'] = int(data['start'])
    data['end'] = int(data['end'])

    output = Models.getTrackModelSummaries(data)

    if output is None:
        return Response(status=204)
    return output


if cfg.testing:
    @view_config(route_name='modelSumUpload')
    def modelSumUploadView(request):
        Models.modelSumUpload(request.json_body)
        return Response(200)

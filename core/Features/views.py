import json
from core import dfDataOut
from core.Features import Features
from pyramid.view import view_config
from pyramid.response import Response


@view_config(route_name='features', request_method='PUT', renderer='json')
def putFeatures(request):
    # Unpacks the data into 1 dict
    data = {**request.matchdict, **request.json_body}

    if Features.putFeatures(data):
        return Response(status=200)

    return Response(status=404)


@view_config(route_name='features', request_method='GET', renderer='json')
def getFeatures(request):
    # Unpacks the data into 1 dict
    data = {**request.matchdict, **request.params}

    out = Features.getFeatures(data)

    if out is None:
        return Response(status=204)
    return out


@view_config(route_name='allFeatures', request_method='GET')
@dfDataOut
def getAllFeatures(request):
    # Unpacks the data into 1 dict
    data = {**request.matchdict, **request.params}

    out = Features.getAllFeatures(data)

    if out is None:
        return Response(status=204)
    return out


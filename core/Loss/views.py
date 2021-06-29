import json
from core.Loss import Loss
from core import dfDataOutShrink
from pyramid.view import view_config
from pyramid.response import Response


@view_config(route_name='loss', request_method='PUT', renderer='json')
def putLoss(request):
    data = {**request.matchdict, **request.json_body}

    if Loss.putLoss(data):
        return Response(status=200)

    return Response(status=404)


@view_config(route_name='loss', request_method='GET', renderer='json')
@dfDataOutShrink
def getLoss(request):
    # Unpacks the data into 1 dict
    data = {**request.matchdict, **request.params}



    return Loss.getLoss(data)

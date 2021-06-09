import json
from core.Loss import Loss
from pyramid.view import view_config
from pyramid.response import Response


@view_config(route_name='loss', request_method='PUT', renderer='json')
def putLoss(request):
    data = {**request.matchdict, **request.json_body}

    if Loss.putLoss(data):
        print('loss good')
        return Response(status=200)

    return Response(status=404)
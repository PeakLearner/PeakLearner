from core.Prediction import Prediction
from pyramid.view import view_config


@view_config(route_name='goNoPredict', request_method='GET', renderer='json')
def getLabeledRegion(request):
    query = {**request.matchdict}

    return Prediction.goToRegionWithNoPrediction(query)


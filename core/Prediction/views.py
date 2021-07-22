from pyramid.view import view_config
from core.util import PLConfig as cfg
from pyramid.response import Response
from core.Prediction import Prediction

if cfg.testing:
    @view_config(route_name='runPrediction', request_method='GET', renderer='json')
    def getLabeledRegion(request):
        Prediction.runPrediction({})
        return Response(status=204)


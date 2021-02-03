from api.Handlers.Handler import TrackHandler
from api.util import PLdb as db


class FeatureHandler(TrackHandler):
    key = 'features'
    """Handles Feature Commands"""

    def do_POST(self, data):
        return self.getCommands()[data['command']](data['args'])

    @classmethod
    def getCommands(cls):
        return {'get': getFeatures,
                'put': putFeatures,
                'getAll': getAllFeatures}


def getFeatures(data):
    problem = data['problem']
    features = db.Features(data['user'], data['hub'], data['track'], problem['chrom'], problem['chromStart'])
    return features.get()


def getAllFeatures(data):
    print(data)


def putFeatures(data):
    problem = data['problem']
    features = db.Features(data['user'], data['hub'], data['track'], problem['chrom'], problem['chromStart'])
    features.put(data['data'])

from api.Handlers.Handler import Handler

changes = 0


def change():
    global changes
    changes = changes + 1


class PredictionHandler(Handler):

    def do_POST(self, data):
        return self.getCommands()[data['command']](data['args'])

    @classmethod
    def getCommands(cls):
        return {'get': get,
                'check': check}


def get(data):
    return data


def check(data):
    if changes > 1:
        return True
    return False

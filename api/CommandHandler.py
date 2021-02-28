from api.Handlers import *


def runHubCommand(query, method, *data):
    if method == 'GET':
        if 'json' in query['handler']:
            data = {'command': 'getJson', 'args': {'file': query['handler']}}
            query['handler'] = 'getJson'
            return HubHandler(query).runCommand(method, data)
        else:
            print(query['handler'], 'not yet implemented')
            return
    elif method == 'POST':
        (data,) = data
        return HubHandler(query).runCommand(method, data)
    else:
        print(method, 'not yet implemented')
        return


def runTrackCommand(query, method, *data):
    handler = TrackHandler.getHandlerByKey(query['handler'])
    if handler is None:
        print(query['handler'], 'not yet implemented')
        return
    if method == 'GET':
        handlerToRun = handler(query)
        return handlerToRun.runCommandWithQuery(method, {'args': {}})
    elif method == 'POST':
        # Because it is *data in args, data needs to be unpacked as it is a tuple
        (data,) = data
        handlerToRun = handler(query)
        return handlerToRun.runCommandWithQuery(method, data)
    else:
        print(method, 'not yet implemented')

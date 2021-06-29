import json
from pyramid.response import Response


def dfDataOut(func):
    def wrap(request):
        if 'Accept' in request.headers:
            outputType = request.headers['Accept']
        else:
            outputType = 'application/json'

        output = func(request)

        if isinstance(output, Response):
            return output

        if outputType is None:
            output['user'] = request.authenticated_userid
            return output

        if outputType == 'json' or outputType == 'application/json' or outputType == '*/*':
            outputDict = output.to_dict('records')
            return Response(json.dumps(outputDict), charset='utf8', content_type='application/json')

        elif outputType == 'csv' or outputType == 'text/csv':
            return Response(output.to_csv(sep='\t', index=False), charset='utf8', content_type='text/csv')
        else:
            return Response(status=404)

    return wrap


def dfDataOutShrink(func):
    def wrap(request):
        if 'Accept' in request.headers:
            outputType = request.headers['Accept']
        else:
            outputType = 'application/json'

        output = func(request)

        if isinstance(output, Response):
            return output

        if outputType is None:
            output['user'] = request.authenticated_userid
            return output

        if outputType == 'json' or outputType == 'application/json' or outputType == '*/*':
            output = output.to_dict('records')
            if isinstance(output, list):
                if len(output) == 1:
                    output = output[0]
            return Response(json.dumps(output), charset='utf8', content_type='application/json')

        elif outputType == 'csv' or outputType == 'text/csv':
            return Response(output.to_csv(sep='\t', index=False), charset='utf8', content_type='text/csv')
        else:
            return Response(status=404)

    return wrap

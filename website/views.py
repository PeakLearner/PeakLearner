from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response
from pyramid.view import view_config
from api import CommandHandler
from api.Handlers import Hubs


@view_config(route_name='home', renderer='index.html')
def home(request):
    return {}


@view_config(route_name='about', renderer='about.html')
def about(request):
    return {}


@view_config(route_name='hubData', renderer='json')
def hubData(request):
    query = request.matchdict
    if request.method == 'GET':
        return CommandHandler.runHubCommand(query, request.method)

    elif request.method == 'POST':
        return CommandHandler.runHubCommand(query, request.method, request.json_body)


@view_config(route_name='trackData', renderer='json')
def trackData(request):
    query = request.matchdict
    if 'GET' == request.method:
        return CommandHandler.runTrackCommand(query, request.method)
    if 'POST' == request.method:
        return CommandHandler.runTrackCommand(query, request.method, request.json_body)
    return []


@view_config(route_name='newHub', renderer='newHub.html')
def newHub(request):
    return {}

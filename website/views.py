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



@view_config(route_name='newHub', renderer='newHub.html')
def newHub(request):
    return {}


@view_config(route_name='tutorial', renderer='tutorial.html')
def tutorial(request):
    return {}


# account views
@view_config(route_name='register', renderer='register.html')
def register(request):
    return {}

@view_config(route_name='login', renderer='login.html')
def login(request):
    return {}

@view_config(route_name='success', renderer='success.html')
def success(request):
    return {}

# account get/post requests
@view_config(route_name='login', request_method='POST')
def loginAttempt(request):
    url = request.route_url('success')
    return HTTPFound(location=url)

@view_config(route_name='logout', request_method='GET')
def logout(request):
    url = request.route_url('login')
    return HTTPFound(location=url)
from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response
from pyramid.view import view_config
from pyramid.view import forbidden_view_config
from api import CommandHandler
from api.Handlers import Hubs

from pyramid_google_login import *
from pyramid.security import authenticated_userid, remember
from pyramid.security import forget

from website.users.Users import USERS
from website.users.User import User

# adds user to USERS dict object
def _create_user(email, **kw):
    newUser = User(email, **kw)
    USERS[newUser.email] = newUser
    return USERS[newUser.email]

# PAGE RENDERS
@view_config(route_name='home', renderer='index.html')
def home(request):
    user = request.unauthenticated_userid
    if not user:
        user = 'Not Logged In'
    return {'user':user}

@view_config(route_name='about', renderer='about.html')
def about(request):
    return {}

@view_config(route_name='newHub', renderer='newHub.html')
def newHub(request):
    return {}

@view_config(route_name='tutorial', renderer='tutorial.html')
def tutorial(request):
    return {}

# auhtentication views
@view_config(route_name='login', renderer='login.html')
def login(request):
    url=request.route_url('auth_signin_redirect')
    return HTTPFound(location=url)

# process user logout
@view_config(route_name='logout', request_method='GET')
def logout(request):
    headers = forget(request)
    url=request.route_url('auth_logout')
    return HTTPFound(location=url, headers=headers)

# check user login credentials
@view_config(route_name='authenticate')
def loginAttempt(request):
    userid = request.unauthenticated_userid
    if userid:
        url = request.route_url('home')
        return HTTPFound(location=url)

    url = request.route_url('failed')
    return HTTPFound(location=url)

@view_config(route_name='failed', renderer='failed.html')
def failed(request):
    return {}

# reroute from pyramid_google_login signin page
@view_config(route_name='auth_signin')
def gohome(request):
    url=request.route_url('home')
    return HTTPFound(location=url)
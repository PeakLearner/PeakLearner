from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response
from pyramid.view import view_config
from pyramid.view import forbidden_view_config
from api import CommandHandler
from api.Handlers import Hubs

from pyramid.security import remember
from pyramid.security import forget

from website.users.Users import USERS
from website.users.User import User

# adds user to USERS dict object
def _create_user(login, password, **kw):
    newUser = User(login, password, **kw)
    USERS[newUser.username] = newUser
    return USERS[newUser.username]

# create TEST USERS
_create_user('zsw23', '123', groups=['admin'])
_create_user('jesus', '123', groups=['admin'])


# PAGE RENDERS
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
@view_config(route_name='login', renderer='login.html')
def login(request):
    return {}

@view_config(route_name='register', renderer='register.html')
def register(request):
    return {}

# display all registered users
@view_config(route_name='success', renderer='success.html')
def success(request):
    login = request.authenticated_userid
    user = USERS.get(login)
    return {'user':user,
            'users':USERS}


# account get/post requests

# check user login credentials
@view_config(route_name='login', request_method='POST')
def loginAttempt(request):

    username = request.params['username']
    password = request.params['password']

    if username in USERS:

        user = USERS.get(username)

        if user and user.check_password(password):
            url = request.route_url('success')
            headers = remember(request, username)
            return HTTPFound(location=url, headers=headers)
    
    url = request.route_url('login')
    return HTTPFound(location=url)

# process user logout
@view_config(route_name='logout', request_method='GET')
def logout(request):
    headers = forget(request)
    url = request.route_url('login')
    return HTTPFound(location=url, headers=headers)

# attempt to create a user profile
@view_config(route_name='register', request_method='POST')
def createUser(request):
    username = request.params['username']
    password = request.params['password']

    # make sure not already an account
    if username not in USERS.keys():
        _create_user(username, password)
        url = request.route_url('login')
        
        return HTTPFound(location=url)

    url = request.route_url('register')
    return HTTPFound(location=url)

# @forbidden_view_config()
# def unauthenticated(context, request):
#     print("\n===FORBIDDEN===\n")
#     url = request.route_url('login')
#     return HTTPFound(location=url)

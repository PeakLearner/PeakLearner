from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response
from pyramid.view import view_config
from api import CommandHandler
from api.Handlers import Hubs

from pyramid.security import remember
from pyramid.security import forget

from website.users.Users import USERS
from website.users.User import User


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

@view_config(route_name='success', renderer='success.html')
def success(request):
    user = request.context
    print("\n",user,"\n")
    return {'user':user,
            'users':USERS}

# account get/post requests
@view_config(route_name='login', request_method='POST')
def loginAttempt(request):

    email = request.params['email']
    password = request.params['password']

    if(email in USERS):

        user = USERS[email]

        if(user and user.check_password(password)):
            url = request.route_url('success')
            headers = remember(request, email)
            return HTTPFound(location=url, headers=headers)
    
    url = request.route_url('login')
    return HTTPFound(location=url)


@view_config(route_name='logout', request_method='GET')
def logout(request):
    url = request.route_url('login')
    return HTTPFound(location=url)

@view_config(route_name='register', request_method='POST')
def createUser(request):
    username = request.params['email']
    password = request.params['password']

    # make sure not already an account
    if(username not in USERS.keys()):
        user = User(username, password)
        USERS[username] = user
        url = request.route_url('login')
        return HTTPFound(location=url)

    url = request.route_url('register')
    return HTTPFound(location=url)
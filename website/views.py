from pyramid.view import view_config
from pyramid.view import view_defaults
from pyramid.view import forbidden_view_config
from api import CommandHandler
from api.Handlers import Hubs
from api.util import PLdb as db
from api.Handlers import Models, Labels, Jobs

from pyramid_google_login.events import UserLoggedIn
from pyramid.events import subscriber

from pyramid_google_login import *
from pyramid.security import remember, forget

from website.users.Users import USERS
from website.users.User import User

# listens for login attempt
# @subscriber(UserLoggedIn)
# def getToken(event):
#     userid = event.userid
#     token = event.oauth2_token
#     if userid not in USERS:
#         _create_user(userid, token)

# adds user to USERS dict object
def _create_user(userid, **kw):
    newUser = User(userid, **kw)
    USERS[newUser.token] = newUser
    return USERS[newUser.token]

# PAGE RENDERS
@view_config(route_name='home', renderer='index.html')
def home(request):

    user = request.authenticated_userid

    return {'user':user}

@view_config(route_name='about', renderer='about.html')
def about(request):

    user = request.authenticated_userid

    return {'user':user}


@view_config(route_name='newHub', renderer='newHub.html')
def newHub(request):
    
    user = request.authenticated_userid

    return {'user':user}

@view_config(route_name='tutorial', renderer='tutorial.html')
def tutorial(request):
    
    user = request.authenticated_userid

    return {'user':user}

# authentication views
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

        if userid in USERS:
            user = USERS[userid]

        else:
            user = _create_user(userid)

        if user.check_token(userid):
            headers=remember(request, userid)
            url = request.route_url('home')
            return HTTPFound(location=url, headers=headers)

    url = request.route_url('failed')
    return HTTPFound(location=url)

@view_config(route_name='failed', renderer='failed.html')
def failed(request):

    user = request.authenticated_userid

    return {'user':user}

# reroute from pyramid_google_login signin page
@view_config(route_name='auth_signin')
def gohome(request):
    url=request.route_url('home')
    return HTTPFound(location=url)

@view_config(route_name='backup', renderer='backup.html')
def backup(request):
    user = request.authenticated_userid
    return {'last_backup': db.getLastBackup(),
            'backups': db.getAvailableBackups(),
            'user':user}


@view_config(route_name='stats', renderer='stats.html')
def stats(request):
    numLabeledChroms, numLabels = Labels.stats()
    currentJobStats = Jobs.stats()

    user = request.authenticated_userid

    return {'numModels': Models.numModels(),
            'numLabeledChroms': numLabeledChroms,
            'numLabels': numLabels,
            'numJobs': currentJobStats['numJobs'],
            'newJobs': currentJobStats['newJobs'],
            'queuedJobs': currentJobStats['queuedJobs'],
            'processingJobs': currentJobStats['processingJobs'],
            'doneJobs': currentJobStats['doneJobs'],
            'avgTime': currentJobStats['avgTime'],
            'user':user}


# TODO: Maybe make these stats user specific?
@view_config(route_name='modelStats', renderer='stats/models.html')
def modelStats(request):
    user = request.authenticated_userid

    return {'numModels': Models.numModels(),
            'correctModels': Models.numCorrectModels(),
            'user':user}


@view_config(route_name='labelStats', renderer='stats/labels.html')
def modelStats(request):
    numLabeledChroms, numLabels = Labels.stats()

    user = request.authenticated_userid

    return {'numLabeledChroms': numLabeledChroms,
            'numLabels': numLabels,
            'user':user}


@view_config(route_name='jobStats', renderer='stats/jobs.html')
def jobStats(request):
    stats = Jobs.stats()
    user = request.authenticated_userid
    stats.update({'user':user})
    return stats


from api.util import PLdb as db
from api.Handlers import Models, Labels, Jobs
from pyramid.view import view_config
from pyramid.security import remember, forget
from pyramid_google_login import *
from website.users.Users import USERS
from website.users.User import User


def _create_user(userid, **kw):
    """Creates a new user when someone logs in with a new email

    Parameters
    ----------
    userid: given a userid(email) adds a new user with that id to a dictionary of users by creating a new User object.
    **kw: optional parameter of groups. So examples of how to call this function include: _create_user(email) or
        _create_user(email, groups=["admin"])

    Returns
    -------
    USERS: dictionary containing the new User object with their token as the key
    """

    new_user = User(userid, **kw)
    USERS[new_user.token] = new_user
    return USERS[new_user.token]


@view_config(route_name='home', renderer='index.html')
def home(request):
    """Home page renderer

    Returns
    -------
    user: userid(email) to be displayed in navbar and welcome message.
    """

    user = request.authenticated_userid
    return {'user': user}


@view_config(route_name='about', renderer='about.html')
def about(request):
    """About page renderer

    Returns
    -------
    user: userid(email) to be displayed in navbar.
    """

    user = request.authenticated_userid
    return {'user': user}


@view_config(route_name='newHub', renderer='newHub.html')
def newHub(request):
    """Upload hub renderer

    Returns
    -------
    user: userid(email) to be displayed in navbar.
    """

    user = request.authenticated_userid
    return {'user': user}


@view_config(route_name='tutorial', renderer='tutorial.html')
def tutorial(request):
    """Tutorial page renderer

    Returns
    -------
    user: userid(email) to be displayed in navbar.
    """

    user = request.authenticated_userid
    return {'user': user}


@view_config(route_name='login', renderer='login.html')
def login(request):
    """When user clicks login button they are redirected to google sign in page

    Redirects
    -------
    auth_signing_redirect: route provided by the pyramid_google_login library which prompts user for google account
    """

    url = request.route_url('auth_signin_redirect')
    return HTTPFound(location=url)


@view_config(route_name='logout', request_method='GET')
def logout(request):
    """Process logout of user

    uses forget() to remove authenticated userid from session

    Redirects
    -------
    auth_logout: route provided by the pyramid_google_login library which process google account logout
    """

    headers = forget(request)
    url = request.route_url('auth_logout')
    return HTTPFound(location=url, headers=headers)


@view_config(route_name='authenticate')
def loginAttempt(request):
    """Conducts authentication attempt by determining if unauthenticated id can be authenticated

    Receives unauthenticated userid from session after a google account is logged in too.
    If the user exists check token stored against googles given token and authenticate user.
    If user does not exist in USERS then call _create_user() to create a new User object with the new user email.
    If successful calling request.authenticated_userid should return the logged in user id.

    Redirects
    -------
    home: redirected to homepage route if successful authentication
    failed: redirect to failed route if unsuccessful which is the home route with a failed authentication alert window
    """

    userid = request.unauthenticated_userid

    if userid:

        # TODO: Convert USERS to database object instead of local dictionary. If necessary.

        if userid in USERS:
            user = USERS[userid]

        else:
            user = _create_user(userid)

        if user.check_token(userid):
            headers = remember(request, userid)
            url = request.route_url('home')
            return HTTPFound(location=url, headers=headers)

    url = request.route_url('failed')
    return HTTPFound(location=url)


@view_config(route_name='failed', renderer='failed.html')
def failed(request):
    """Displays window alert indicating failed authentication

    failed.html display simply displays the window alert indicating authentication failure and then reroutes to
    home after clicking OK.

    Returns
    -------
    user: userid(email) to be displayed in navbar.
    """

    user = request.authenticated_userid
    return {'user': user}


# reroute from pyramid_google_login sign-in page
@view_config(route_name='auth_signin')
def go_home(request):
    """Skips the pyramid_google_login library page which is pointless for our purposes because
    after authentication we simply want to reroute to our homepage

    Redirects
    -------
    home: homepage route is redirected to from the pyramid_google_login library rout eof auth_signin
    """

    url = request.route_url('home')
    return HTTPFound(location=url)


@view_config(route_name='backup', renderer='backup.html')
def backup(request):
    """TODO: Document this view"""

    user = request.authenticated_userid
    return {'last_backup': db.getLastBackup(),
            'backups': db.getAvailableBackups(),
            'user': user}


@view_config(route_name='stats', renderer='stats.html')
def stats(request):
    """TODO: Document this view"""

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
            'user': user}


# TODO: Maybe make these stats user specific?
@view_config(route_name='modelStats', renderer='stats/models.html')
def modelStats(request):
    """TODO: Document this view"""

    user = request.authenticated_userid

    return {'numModels': Models.numModels(),
            'correctModels': Models.numCorrectModels(),
            'user': user}


@view_config(route_name='labelStats', renderer='stats/labels.html')
def modelStats(request):
    """TODO: Document this view"""

    numLabeledChroms, numLabels = Labels.stats()

    user = request.authenticated_userid

    return {'numLabeledChroms': numLabeledChroms,
            'numLabels': numLabels,
            'user': user}


@view_config(route_name='jobStats', renderer='stats/jobs.html')
def jobStats(request):
    """TODO: Document this view"""

    job_stats = Jobs.stats()
    user = request.authenticated_userid
    job_stats.update({'user': user})
    return job_stats

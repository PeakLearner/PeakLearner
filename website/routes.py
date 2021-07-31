from core.util import PLdb as db, PLConfig as cfg
from core.Models import Models
from core.Jobs import Jobs
from core.Labels import Labels
from core.Hubs import Hubs

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

templates = Jinja2Templates(directory='website/templates')


@router.get('/', response_class=HTMLResponse)
def home(request: Request):
    """Home page renderer

    Returns
    -------
    user: userid(email) to be displayed in navbar and welcome message.
    """
    user = request.session.get('user')

    if user is None:
        user = 'Public'
    else:
        user = user['email']

    return templates.TemplateResponse('index.html', {'request': request, 'user': user})


@router.get('/about', response_class=HTMLResponse)
def about(request: Request):
    """About page renderer

    Returns
    -------
    user: userid(email) to be displayed in navbar.
    """
    user = request.session.get('user')

    if user is None:
        user = 'Public'
    else:
        user = user['email']

    return templates.TemplateResponse('about.html', {'request': request, 'user': user})


@router.get('/help', response_class=HTMLResponse)
def help(request: Request):
    user = request.session.get('user')

    if user is None:
        user = 'Public'
    else:
        user = user['email']

    return templates.TemplateResponse('help.html', {'request': request, 'user': user})


@router.get('/newHub', response_class=HTMLResponse)
def newHub(request: Request):
    """Upload hub renderer

    Returns
    -------
    user: userid(email) to be displayed in navbar.
    """
    user = request.session.get('user')

    if user is None:
        user = 'Public'
    else:
        user = user['email']

    return templates.TemplateResponse('newHub.html', {'request': request, 'user': user})


@router.get('/tutorial', response_class=HTMLResponse)
def tutorial(request: Request):
    """Tutorial page renderer

    Returns
    -------
    user: userid(email) to be displayed in navbar.
    """
    user = request.session.get('user')

    if user is None:
        user = 'Public'
    else:
        user = user['email']

    return templates.TemplateResponse('tutorial.html', {'request': request, 'user': user})


@router.get('/stats', response_class=HTMLResponse)
def statsView(request: Request):
    """TODO: Document this view"""
    user = request.session.get('user')

    if user is None:
        user = 'Public'
    else:
        user = user['email']

    numLabeledChroms, numLabels = Labels.labelsStats({})
    currentJobStats = Jobs.jobsStats({})

    return templates.TemplateResponse('stats.html', {'request': request,
                                                     'numModels': Models.numModels(),
                                                     'numLabeledChroms': numLabeledChroms,
                                                     'numLabels': numLabels,
                                                     'numJobs': currentJobStats['numJobs'],
                                                     'newJobs': currentJobStats['newJobs'],
                                                     'queuedJobs': currentJobStats['queuedJobs'],
                                                     'processingJobs': currentJobStats['processingJobs'],
                                                     'doneJobs': currentJobStats['doneJobs'],
                                                     'avgTime': currentJobStats['avgTime'],
                                                     'user': user})


# TODO: Maybe make these stats user specific?
@router.get('/model', response_class=HTMLResponse)
def modelStats(request: Request):
    """TODO: Document this view"""
    user = request.session.get('user')

    if user is None:
        user = 'Public'
    else:
        user = user['email']

    return templates.TemplateResponse('stats/models.html', {'request': request,
                                                            'numModels': Models.numModels(),
                                                            'correctModels': Models.numCorrectModels(),
                                                            'user': user})


@router.get('/label', response_class=HTMLResponse)
def labelStats(request: Request):
    user = request.session.get('user')

    if user is None:
        user = 'Public'
    else:
        user = user['email']

    numLabeledChroms, numLabels = Labels.labelsStats({})

    return templates.TemplateResponse('stats/labels.html', {'request': request,
                                                            'numLabeledChroms': numLabeledChroms,
                                                            'numLabels': numLabels,
                                                            'user': user})


@router.get('/myHubs', response_class=HTMLResponse)
def getMyHubs(request: Request):
    """My Hubs page renderer

    Loops through each db.HubInfo item in the database in which the current authenticated user is either the owner or
    is a co user given access by another user.

    Returns
    -------
    user: userid(email) to be displayed in navbar, page title, and to determine which hubs are owned vs shared.
    hubInfos: dictionary of db.HubInfo objects accessible by a key of that hubs name
    usersdict: dictionary containing each hub name as a key and its users in a list as values
    permissions: dictionary containing the key of (hub name, user) in which the user is the one in which the value
        of that dict item is a dictionary of that users permissions.
    labels: dictionary of each label accessible by a key being the hub name
    """

    # TODO: Authentication

    user = request.session.get('user')

    if user is None:
        user = 'Public'
    else:
        user = user['email']

    out = Hubs.getHubInfosForMyHubs(user)
    out['request'] = request
    out['user'] = user

    return templates.TemplateResponse('myHubs.html', out)

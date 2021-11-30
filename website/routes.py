from core.Permissions import Permissions
from core.util import PLConfig as cfg
from core.Models import Models
from core.Jobs import Jobs
from core.Labels import Labels
from core.Hubs import Hubs
from core.User import User

from sqlalchemy.orm import Session
from fastapi import APIRouter, Request, Response, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import core

router = APIRouter()

templates = Jinja2Templates(directory='website/templates')


@router.get('/', response_class=HTMLResponse, include_in_schema=False)
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


@router.get('/about', response_class=HTMLResponse, include_in_schema=False)
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


@router.get('/help', response_class=HTMLResponse, include_in_schema=False)
def help(request: Request):
    user = request.session.get('user')

    if user is None:
        user = 'Public'
    else:
        user = user['email']

    return templates.TemplateResponse('help.html', {'request': request, 'user': user})


@router.get('/newHub', response_class=HTMLResponse, include_in_schema=False)
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


@router.get('/tutorial', response_class=HTMLResponse, include_in_schema=False)
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


@router.get('/stats', response_class=HTMLResponse, include_in_schema=False)
def statsView(request: Request,
              db: Session = Depends(core.get_db)):
    """TODO: Document this view"""
    user = request.session.get('user')

    if user is None:
        user = 'Public'
    else:
        user = user['email']

    numLabeledChroms, numLabels = Labels.labelsStats(db)
    currentJobStats = Jobs.jobsStats(db)

    return templates.TemplateResponse('stats.html', {'request': request,
                                                     'numLabeledChroms': numLabeledChroms,
                                                     'numLabels': numLabels,
                                                     **currentJobStats,
                                                     'user': user})


@router.get('/label', response_class=HTMLResponse, include_in_schema=False)
def labelStats(request: Request,
               db: Session = Depends(core.get_db)):
    user = request.session.get('user')

    if user is None:
        user = 'Public'
    else:
        user = user['email']

    numLabeledChroms, numLabels = Labels.labelsStats(db)

    return templates.TemplateResponse('stats/labels.html', {'request': request,
                                                            'numLabeledChroms': numLabeledChroms,
                                                            'numLabels': numLabels,
                                                            'user': user})


@router.get('/myHubs', response_class=HTMLResponse, include_in_schema=False)
def getMyHubs(request: Request, db: Session = Depends(core.get_db)):
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

    authUser = User.getAuthUser(request, db)

    out = Hubs.getHubInfosForMyHubs(db, authUser)
    out['request'] = request
    out['user'] = authUser.name

    return templates.TemplateResponse('myHubs.html', out)


@router.get('/admin', response_class=HTMLResponse, include_in_schema=False)
def admin(request: Request):
    user = request.session.get('user')

    if user is None:
        user = 'Public'
    else:
        user = user['email']

    if not Permissions.hasAdmin(user):
        return Response(status_code=403)

    return templates.TemplateResponse('admin.html', {'request': request, 'user': user})


@router.get('/addAdmin', include_in_schema=False)
def addAdmin(request: Request, email: str):
    user = request.session.get('user')

    if user is None:
        user = 'Public'
    else:
        user = user['email']

    if not Permissions.hasAdmin(user):
        return Response(status_code=403)

    return Permissions.addAdmin(email)

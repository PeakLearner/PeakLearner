from pyramid.view import view_config
from api.Handlers import Jobs, Hubs
from api.util import PLdb as db
from api import CommandHandler
import json

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


@view_config(route_name='jobInfo', renderer='json')
def jobStatus(request):
    return Jobs.getAllJobs({})


@view_config(route_name='jobs', renderer='json')
def jobs(request):
    query = request.matchdict
    if 'GET' == request.method:
        return Jobs.getAllJobs({})
    if 'POST' == request.method:
        return Jobs.JobHandler(query).runCommand(request.method, request.json_body)
    return []

@view_config(route_name='myHubs', renderer='myHubs.html')
def myHubs(request):
    userid = request.authenticated_userid
    keys = db.HubInfo.keysWhichMatch(db.HubInfo, userid)
    HubNames = list(map(lambda tuple: tuple[1], keys))
    
    hubInfo = db.HubInfo("jdh553@nau.edu", "TestHub").get()

    usersdict = {}
    for hubName in HubNames:
        currHubInfo = db.HubInfo(userid, hubName).get()

        usersdict[hubName] = currHubInfo['users'] if 'users' in currHubInfo.keys() else []

    return {"userid" : userid, "HubNames" : HubNames, "hubInfo" : hubInfo, "usersdict" : usersdict}

@view_config(route_name='addUser', request_method='POST')
def addUser(request):
    userid = request.unauthenticated_userid
    keys = db.HubInfo.keysWhichMatch(db.HubInfo, userid)

    userEmail = request.params['userEmail']
    hubName = request.params['hubName']

    hubInfo = db.HubInfo(userid, hubName).get()
    if 'users' in hubInfo.keys():
        hubInfo['users'].append(userEmail)
    else:   
        hubInfo['users'] = []
        hubInfo['users'].append(userEmail)
    
    hubInfo['users'] = list(set(hubInfo['users']))
    db.HubInfo(userid, hubName).put(hubInfo)

    print(db.HubInfo(userid, hubName).get())


    url = request.route_url('myHubs')
    return HTTPFound(location=url)

@view_config(route_name='uploadHubUrl', renderer='json')
def uploadHubUrl(request):
    user = request.unauthenticated_userid
    if 'POST' == request.method:
        # TODO: Implement user authentication (and maybe an anonymous user?)
        return Hubs.parseHub({'user': user, 'url': request.json_body['args']['hubUrl']})
    return


@view_config(route_name='hubInfo', renderer='json')
def hubInfo(request):
    query = request.matchdict
    return Hubs.getHubInfo(query['user'], query['hub'])


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


@view_config(route_name='doBackup', renderer='json')
def runBackup(request):
    return db.doBackup()


@view_config(route_name='doRestore', renderer='json')
def runRestore(request):
    if 'POST' == request.method:
        return db.doRestoreWithSelected(request.POST['toRestore'])

    return db.doRestore()

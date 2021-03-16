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

from pyramid_google_login import *


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
    hubNames = list(map(lambda tuple: tuple[1], keys))

    everyKey = db.HubInfo.keysWhichMatch(db.HubInfo)
    everyUser = list(map(lambda tuple: tuple[0], everyKey))
    everyHubName = list(map(lambda tuple: tuple[1], everyKey))
    permissions = {}



    # print(mylabels)
    # mylabels = dict(('{hubName}'.format(hubName = key), mylabels[key].shape[0]) for key in mylabels.keys())
    # print(mylabels)

    # all_usersdict = {}
    # for hubName in everyHubName:
    #     currHubInfo = db.HubInfo(userid, hubName).get()
    #     all_usersdict[hubName] = currHubInfo['users'] if 'users' in currHubInfo.keys() else []

    myHubInfos = dict(
        ('{hubName}'.format(hubName=key[1]), db.HubInfo(key[0], key[1]).get())
        for key in keys
    )

    mylabels = {}

    usersdict = {}
    for hubName in hubNames:
        currHubInfo = db.HubInfo(userid, hubName).get()

        usersdict[hubName] = currHubInfo['users'] if 'users' in currHubInfo.keys() else []

        myKeys = db.Labels.keysWhichMatch(userid, hubName)
        num_labels = 0
        for key in myKeys:
            num_labels += db.Labels(*key).get().shape[0]
            # num_labels += 1

        mylabels[hubName] = num_labels
        # print(myKeys)
        # mylabels.update(dict(('{hubName}'.format(hubName=key[1]), db.Labels(key[0],key[1],key[2],key[3]).get())
        #                 for key in myKeys))


    sharedLabels = {}
    for hub in everyKey:
        currHubInfo = db.HubInfo(hub[0], hub[1]).get()
        try:
            if userid in currHubInfo['users']:
                sharedKeys = db.Labels.keysWhichMatch(hub[0],hub[1])
                num_labels = 0
                for key in sharedKeys:
                    num_labels += db.Labels(*key).get().shape[0]
                sharedLabels[hub[1]] = num_labels

        except KeyError:
            pass
        finally:
            pass

    otherHubInfos = {}
    for key in everyKey:
        currentHub = db.HubInfo(key[0], key[1]).get()
        currentHub['owner'] = key[0]

        try:
            if userid in currentHub['users']:
                otherHubInfos['{hubName}'.format(hubName=key[1])] = currentHub
        except KeyError:
            pass
        finally:
            pass

    for hubName in hubNames:
        for couser in usersdict[hubName]:
            permissions[(hubName, couser)] = db.Permissions(userid, hubName, couser).get()

    return {"user": userid,
            "HubNames": hubNames,
            "myHubInfos": myHubInfos,
            "otherHubInfos": otherHubInfos,
            "usersdict": usersdict,
            "permissions": permissions,
            "mylabels": mylabels,
            "sharedlabels": sharedLabels}


@view_config(route_name='publicHubs', renderer='publicHubs.html')
def publicHubs(request):
    userid = request.authenticated_userid

    everyKey = db.HubInfo.keysWhichMatch(db.HubInfo)
    everyUser = list(map(lambda tuple: tuple[0], everyKey))
    everyHubName = list(map(lambda tuple: tuple[1], everyKey))

    hubNames = list(map(lambda tuple: tuple[1], everyKey))

    hubInfos = {}
    myLabels = {}
    for key in everyKey:
        currentHub = db.HubInfo(key[0], key[1]).get()
        
        if('isPublic' in currentHub.keys() and currentHub['isPublic']):
            currentHub['labels'] = 0
            for labelKey in db.Labels.keysWhichMatch(key[0], key[1]):
                currentHub['labels'] += db.Labels(*labelKey).get().shape[0]

            currentHub['owner'] = key[0]
            try:
                hubInfos['{hubName}'.format(hubName=key[1])] = currentHub
            except KeyError:
                pass
            finally:
                pass
            
            

    return {"user": userid,
            "HubNames": hubNames,
            "hubInfos": hubInfos}


@view_config(route_name='public', request_method='POST')
def isPublic(request):
    userid = request.authenticated_userid
    query = request.matchdict

    hub = query['hub']

    chkpublic = "chkpublic" in request.params.keys()

    hubInfo = db.HubInfo(userid, hub).get()
    hubInfo['isPublic'] = chkpublic
    db.HubInfo(userid, hub).put(hubInfo)

    url = request.route_url('myHubs')
    return HTTPFound(location=url)


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

    url = request.route_url('myHubs')
    return HTTPFound(location=url)


@view_config(route_name='hubRemoveUser', request_method='POST')
def removeUser(request):
    userid = request.unauthenticated_userid
    keys = db.HubInfo.keysWhichMatch(db.HubInfo, userid)
    userEmail = request.params['couserName']
    hubName = request.params['hubName']

    hub_info = db.HubInfo(userid, hubName).get()
    hub_info['users'].remove(userEmail)
    db.HubInfo(userid, hubName).put(hub_info)

    url = request.route_url('myHubs')
    return HTTPFound(location=url)


@view_config(route_name='adjustPerms', renderer='adjustPerms.html')
def adjustPerms(request):
    userid = request.authenticated_userid

    query = request.matchdict

    hubName = query['hub']
    couser = query['couser']
    permissions = db.Permissions(userid, hubName, couser).get()

    return {'user': userid,
            'hub': hubName,
            'couser': couser,
            'permissions': permissions}


@view_config(route_name='adjustPerms', request_method='POST')
def adjustPermsPOST(request):
    userid = request.authenticated_userid
    query = request.matchdict

    user = query['user']
    hub = query['hub']
    couser = query['couser']

    chkpublic = "Can change to public" if "chkpublic" in request.params.keys() else ""
    chkhub = "Can adjust hub" if "chkhub" in request.params.keys() else ""
    chklabels = "Can adjust labels" if "chklabels" in request.params.keys() else ""
    chktracks = "Can change tracks" if "chktracks" in request.params.keys() else ""
    chkmoderator = "Is moderator" if "chkmoderator" in request.params.keys() else ""

    # db.Permissions(user, hub, couser).put({'chkpublic' : chkpublic == 'True',
    #                                         'chkhub' : chkhub == 'True',
    #                                         'chklabels' : chklabels == 'True',
    #                                         'chktracks' : chktracks == 'True',
    #                                         'chkmoderator' : chkmoderator == 'True'})

    db.Permissions(user, hub, couser).put([chkpublic, chkhub, chklabels, chktracks, chkmoderator])

    # print(query)

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

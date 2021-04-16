from pyramid.view import view_config
from api import CommandHandler
from api.util import PLdb as db
from api.Handlers import Models, Labels, Jobs, Hubs

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


@view_config(route_name='moreHubInfo', renderer='moreHubInfo.html')
def moreHubInfo(request):
    userid = request.authenticated_userid
    query = request.matchdict
    hubName = query['hub']

    myKeys = db.Labels.keysWhichMatch(userid, hubName)
    num_labels = 0
    labels = {}
    for key in myKeys:
        num_labels += db.Labels(*key).get().shape[0]
        labels[(key[2], key[3])] = db.Labels(*key).get().to_html()

    thisHubInfo = db.HubInfo(userid, hubName).get()

    tracks = []

    return{'user': userid,
           'hubName': hubName,
           'hubInfo': thisHubInfo,
           'numLabels': num_labels,
           'tracks': tracks,
           'labels': labels}


@view_config(route_name='myHubs', renderer='myHubs.html')
def myHubs(request):
    userid = request.authenticated_userid
    everyKey = db.HubInfo.keysWhichMatch(db.HubInfo)
    hubInfos = Hubs.getHubInfos(everyKey, userid)

    labels = {}
    usersdict = {}
    permissions = {}

    for hubName in hubInfos:

        currHubInfo = hubInfos[hubName]
        owner = currHubInfo['owner']
        usersdict[hubName] = currHubInfo['users'] if 'users' in currHubInfo.keys() else []

        everyLabelKey = db.Labels.keysWhichMatch(owner, hubName)

        num_labels = 0
        for key in everyLabelKey:
            if key[0] == userid or userid in hubInfos[key[1]]['users']:
                num_labels += db.Labels(*key).get().shape[0]

        labels[hubName] = num_labels

        # get each co users permissions
        for couser in usersdict[hubName]:
            permissions[(hubName, couser)] = db.Permissions(owner, hubName, couser).get()

    return {"user": userid,
            "hubInfos": hubInfos,
            "usersdict": usersdict,
            "permissions": permissions,
            "labels": labels}


@view_config(route_name='publicHubs', renderer='publicHubs.html')
def publicHubs(request):
    userid = request.authenticated_userid

    everyKey = db.HubInfo.keysWhichMatch(db.HubInfo)

    hubNames = list(map(lambda tuple: tuple[1], everyKey))

    hubInfos = {}
    for key in everyKey:
        currentHub = db.HubInfo(key[0], key[1]).get()

        if 'isPublic' in currentHub.keys() and currentHub['isPublic']:
            currentHub['labels'] = 0
            for labelKey in db.Labels.keysWhichMatch(key[0], key[1]):
                currentHub['labels'] += db.Labels(*labelKey).get().shape[0]

            currentHub['owner'] = key[0]
            hubInfos['{hubName}'.format(hubName=key[1])] = currentHub

    return {"user": userid,
            "HubNames": hubNames,
            "hubInfos": hubInfos}

# TODO: Transaction
@view_config(route_name='public', request_method='POST')
def isPublic(request):
    txn = db.getTxn()

    query = request.matchdict
    hubName = query['hub']
    user = query['user']

    chkpublic = "chkpublic" in request.params.keys()
    hub = db.HubInfo(user, hubName).get()
    hub['isPublic'] = chkpublic
    db.HubInfo(user, hubName).put(hub, txn=txn)
    txn.commit()
    
    if chkpublic:
        Hubs.addUserToHub(hubName, user, 'Public')
        
    elif 'Public' in hub['users']:
        Hubs.removeUserFromHub(hubName, user, 'Public')

    url = request.route_url('myHubs')
    return HTTPFound(location=url)


@view_config(route_name='addUser', request_method='POST')
def addUser(request):
    newUser = request.params['userEmail']
    hubName = request.params['hubName']
    owner = request.params['owner']

    Hubs.addUserToHub(hubName, owner, newUser)

    url = request.route_url('myHubs')
    return HTTPFound(location=url)


@view_config(route_name='hubRemoveUser', request_method='POST')
def removeUser(request):
    userid = request.unauthenticated_userid
    userToRemove = request.params['couserName']
    hubName = request.params['hubName']

    Hubs.removeUserFromHub(hubName, userid, userToRemove)

    url = request.route_url('myHubs')
    return HTTPFound(location=url)

# TODO: Transaction
@view_config(route_name='addTrack', request_method='POST')
def addTrack(request):
    txn = db.getTxn()
    query = request.matchdict
    hubName = query['hub']
    owner = query['user']
    category = request.params['category']
    trackName = request.params['trackName']
    url = request.params['url']

    hubInfo = db.HubInfo(owner, hubName).get()
    hubInfo['tracks'][trackName] = {'categories': category, 'key': trackName, 'url': url}
    db.HubInfo(owner, hubName).put(hubInfo, txn=txn)
    txn.commit()

    url = request.route_url('myHubs')
    return HTTPFound(location=url)

# TODO: Transaction
@view_config(route_name='removeTrack', request_method='POST')
def removeTrack(request):
    
    txn = db.getTxn()
    query = request.matchdict
    hubName = query['hub']
    owner = query['user']
    trackName = request.params['trackName']

    hubInfo = db.HubInfo(owner, hubName).get()

    del hubInfo['tracks'][trackName]

    db.HubInfo(owner, hubName).put(hubInfo, txn=txn)
    txn.commit()

    url = request.route_url('myHubs')
    return HTTPFound(location=url)

# TODO: transaction
@view_config(route_name='adjustPerms', request_method='POST')
def adjustPermsPOST(request):
    txn = db.getTxn()

    userid = request.authenticated_userid
    query = request.matchdict

    user = query['user']
    hub = query['hub']
    couser = query['couser']

    chkpublic = "Can change to public" if "chkpublic" in request.params.keys() else ""
    chklabels = "Can adjust labels" if "chklabels" in request.params.keys() else ""
    chktracks = "Can change tracks" if "chktracks" in request.params.keys() else ""
    chkmoderator = "Is moderator" if "chkmoderator" in request.params.keys() else ""

    db.Permissions(user, hub, couser).put({'Publicity' : chkpublic, 
    'Labels' : chklabels, 
    'Tracks' : chktracks, 
    'Moderator' : chkmoderator}, txn=txn)
    txn.commit()

    url = request.route_url('myHubs')
    return HTTPFound(location=url)


@view_config(route_name='uploadHubUrl', renderer='json')
def uploadHubUrl(request):
    user = request.authenticated_userid
    if 'POST' == request.method:
        # TODO: Implement user authentication (and maybe an anonymous user

        if not request.json_body['args']['hubUrl']:
            return

        url = request.json_body['args']['hubUrl']
        hubName = ""
        if request.json_body['args']['hubName']:
            hubName = request.json_body['args']['hubName']

        return Hubs.parseHub({'user': user,
                              'url': url,
                              'hubName': hubName})
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

# TODO: Transaction
@view_config(route_name='deleteHub', request_method='POST')
def deleteHub(request):
    txn = db.getTxn()
    userid = request.unauthenticated_userid
    hubName = request.params['hubName']

    hub_info = None
    db.HubInfo(userid, hubName).put(hub_info, txn=txn)
    txn.commit()

    url = request.route_url('myHubs')
    return HTTPFound(location=url)

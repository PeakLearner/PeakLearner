from pyramid.view import view_config
from api import CommandHandler
from api.util import PLdb as db
from api.Handlers import Models, Labels, Jobs, Hubs

from pyramid_google_login import *


@view_config(route_name='jobInfo', renderer='json')
def jobStatus(request):
    """TODO: Document this view"""

    return Jobs.getAllJobs({})


@view_config(route_name='jobs', renderer='json')
def jobs(request):
    """TODO: Document this view"""

    query = request.matchdict
    if 'GET' == request.method:
        return Jobs.getAllJobs({})
    if 'POST' == request.method:
        return Jobs.JobHandler(query).runCommand(request.method, request.json_body)
    return []


@view_config(route_name='moreHubInfo', renderer='moreHubInfo.html')
def moreHubInfo(request):
    """More Hub Info page renderer

    Returns
    -------
    user: userid(email) to be displayed in navbar.
    hubName: String indicating the name of the current Hub
    hubInfo: object containing the db.HubInfo object of the current hub
    numLabels: integer count of the number of labels in the hub
    labels: dictionary of each label accessible by a key being (trackName, chromName)
    """

    userid = request.authenticated_userid
    query = request.matchdict
    hubName = query['hub']
    owner = query['owner']

    myKeys = db.Labels.keysWhichMatch(owner, hubName)
    num_labels = 0
    labels = {}
    for key in myKeys:
        num_labels += db.Labels(*key).get().shape[0]
        # TODO: access the key by dictionary keys instead of 2 and 3 indecies for better readability
        # key[2] = track name | key[3] = chrom name
        print(f"Key2: {key[2]}, Key3: {key[3]}\n")
        labels[(key[2], key[3])] = db.Labels(*key).get().to_html()

    thisHubInfo = db.HubInfo(owner, hubName).get()

    return {'user': userid,
            'owner': owner,
            'hubName': hubName,
            'hubInfo': thisHubInfo,
            'numLabels': num_labels,
            'labels': labels}


@view_config(route_name='myHubs', renderer='myHubs.html')
def myHubs(request):
    """My Hubs page renderer

    Loops through each db.HubInfo item in the database in which the current authenticated user is either the owner or
    is a couser given access by another user.

    Returns
    -------
    user: userid(email) to be displayed in navbar, page title, and to determine which hubs are owned vs shared.
    hubInfos: dictionary of db.HubInfo objects accessible by a key of that hubs name
    usersdict: dictionary containing each hub name as a key and its users in a list as values
    permissions: dictionary containing the key of (hub name, user) in which the user is the one in which the value
        of that dict item is a dictionary of that users permissions.
    labels: dictionary of each label accessible by a key being the hub name
    """

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
    # TODO: Convert public hubs into a search filter on the myHubs page
    """Public Hubs page renderer

    Loops through each db.HubInfo item in the database that has the public permission enabled.

    Returns
    -------
    user: userid(email) to be displayed in navbar and page title.
    HubNames: list of every hub name for every hub Info
    hubInfos: dictionary of db.HubInfo objects accessible by a key of that hubs name
    """

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


@view_config(route_name='public', request_method='POST')
def isPublic(request):
    """Make a hub public from checking the public checkbox on a hub card

    Update the db.HubInfo object from the post request by receiving its hub name and owner userid and creating a
    transaction to update the 'isPublic' dictionary item in the Hub.

    Redirects
    ---------
    myHubs: the route in which the post request is made from initially so that the process of making a hub public is
        seamless.
    """

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
    """Add a user to a db.HubInfo object

    Update the db.HubInfo object from the post request by receiving its hub name and owner userid and then calling the
    addUserToHub function to add that user to the current hub and then refresh the page to reflect that addition.

    Redirects
    ---------
    myHubs: the route in which the post request is made from initially so that the process of adding a user to the
        current hub is seamless.
    """

    newUser = request.params['userEmail']
    hubName = request.params['hubName']
    owner = request.params['owner']

    Hubs.addUserToHub(hubName, owner, newUser)

    url = request.route_url('myHubs')
    return HTTPFound(location=url)


@view_config(route_name='hubRemoveUser', request_method='POST')
def removeUser(request):
    """Remove a user to a db.HubInfo object

    Update the db.HubInfo object from the post request by receiving its hub name and owner userid and then calling the
    removeUserFromHub function to remove that user from the hub, then refreshing the page to reflect that deletion.

    Redirects
    ---------
    myHubs: the route in which the post request is made from initially so that the process of removing a user from the
        current hub is seamless.
    """

    userid = request.unauthenticated_userid
    userToRemove = request.params['couserName']
    hubName = request.params['hubName']

    Hubs.removeUserFromHub(hubName, userid, userToRemove)

    url = request.route_url('myHubs')
    return HTTPFound(location=url)


@view_config(route_name='addTrack', request_method='POST')
def addTrack(request):
    """Add a track to a db.HubInfo object

    Update the db.HubInfo object from the post request by receiving its hub name and owner userid and then conducting a
    transaction in which the HubInfo['tracks'] item in the dictionary is updated with a new dict item with trackName as
    a key and the track info as the value.

    Redirects
    ---------
    myHubs: the route in which the post request is made from initially so that the process of adding a track to the
        current hub is seamless.
    """

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


@view_config(route_name='removeTrack', request_method='POST')
def removeTrack(request):
    """Remove a track from a db.HubInfo object

    Update the db.HubInfo object from the post request by receiving its hub name and owner userid and then conducting a
    transaction in which the HubInfo['tracks'] item in the dictionary is updated by removing a dict item of the track
    name.

    Redirects
    ---------
    myHubs: the route in which the post request is made from initially so that the process of removing a track from the
        current hub is seamless.
    """

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


@view_config(route_name='adjustPerms', request_method='POST')
def adjustPermsPOST(request):
    """Process permission change post requests

    Update the db.HubInfo object from the post request by receiving its hub name, owner userid and the userid of which
    permissions are being changed. Then a transaction is started to update the permissions related to those three
    parameters and updating the permissions to match the post requests inputted changes.

    Redirects
    ---------
    myHubs: the route in which the post request is made from initially so that the process changing hub permissions is
        seamless.
    """

    txn = db.getTxn()

    query = request.matchdict
    user = query['user']
    hub = query['hub']
    couser = query['couser']

    chkpublic = "Can change to public" if "chkpublic" in request.params.keys() else ""
    chklabels = "Can adjust labels" if "chklabels" in request.params.keys() else ""
    chktracks = "Can change tracks" if "chktracks" in request.params.keys() else ""
    chkmoderator = "Is moderator" if "chkmoderator" in request.params.keys() else ""

    db.Permissions(user, hub, couser).put({'Publicity': chkpublic,
                                           'Labels': chklabels,
                                           'Tracks': chktracks,
                                           'Moderator': chkmoderator}, txn=txn)
    txn.commit()

    url = request.route_url('myHubs')
    return HTTPFound(location=url)


@view_config(route_name='uploadHubUrl', renderer='json')
def uploadHubUrl(request):
    """TODO: Document this view"""

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
    """TODO: Document this view"""

    query = request.matchdict
    return Hubs.getHubInfo(query['user'], query['hub'])


@view_config(route_name='hubData', renderer='json')
def hubData(request):
    """TODO: Document this view"""

    query = request.matchdict
    if request.method == 'GET':
        return CommandHandler.runHubCommand(query, request.method)

    elif request.method == 'POST':
        return CommandHandler.runHubCommand(query, request.method, request.json_body)


@view_config(route_name='trackData', renderer='json')
def trackData(request):
    """TODO: Document this view"""

    query = request.matchdict
    query['id'] = request.authenticated_userid
    if 'GET' == request.method:
        return CommandHandler.runTrackCommand(query, request.method)
    if 'POST' == request.method:
        return CommandHandler.runTrackCommand(query, request.method, request.json_body)
    return []


@view_config(route_name='doBackup', renderer='json')
def runBackup(request):
    """TODO: Document this view"""

    return db.doBackup()


@view_config(route_name='doRestore', renderer='json')
def runRestore(request):
    """TODO: Document this view"""

    if 'POST' == request.method:
        return db.doRestoreWithSelected(request.POST['toRestore'])

    return db.doRestore()


@view_config(route_name='deleteHub', request_method='POST')
def deleteHub(request):
    """Delete a db.HubInfo object

    Using a transaction delete a db.HubInfo by replacing it with a None object

    Redirects
    ---------
    myHubs: reroute to page from which deleting is page so that deleting process of a hub is seamless.
    """

    txn = db.getTxn()
    userid = request.unauthenticated_userid
    hubName = request.json_body['args']['hubName']

    hub_info = None
    db.HubInfo(userid, hubName).put(hub_info, txn=txn)
    txn.commit()

    url = request.route_url('myHubs')
    return HTTPFound(location=url)

import json
from core.Hubs import Hubs
from pyramid_google_login import *
from pyramid.view import view_config
from pyramid.response import Response
from core.Permissions import Permissions
from pyramid.httpexceptions import HTTPFound


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

    userid = request.authenticated_userid
    query = request.matchdict
    owner = query['user']
    hub = query['hub']

    args = dict(request.params)

    coUser = args['coUser']

    Permissions.adjustPermissions(owner, hub, userid, coUser, args)

    url = request.route_url('myHubs', _app_url=get_app_url(request))
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

    newUser = request.params['email']
    hub = request.matchdict['hub']
    owner = request.matchdict['user']

    Permissions.addUserToHub(request, owner, hub, newUser)

    url = request.route_url('myHubs', _app_url=get_app_url(request))
    return HTTPFound(location=url)


@view_config(route_name='removeUser', request_method='POST')
def removeUser(request):
    """Remove a user to a db.HubInfo object

    Update the db.HubInfo object from the post request by receiving its hub name and owner userid and then calling the
    removeUserFromHub function to remove that user from the hub, then refreshing the page to reflect that deletion.

    Redirects
    ---------
    myHubs: the route in which the post request is made from initially so that the process of removing a user from the
        current hub is seamless.
    """

    userToRemove = request.params['email']
    hub = request.matchdict['hub']
    owner = request.matchdict['user']

    Hubs.removeUserFromHub(request, owner, hub, userToRemove)

    url = request.route_url('myHubs', _app_url=get_app_url(request))
    return HTTPFound(location=url)

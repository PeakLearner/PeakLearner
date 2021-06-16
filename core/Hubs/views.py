import json
from core.Hubs import Hubs
from core.Labels import Labels
from pyramid_google_login import *
from pyramid.view import view_config
from pyramid.response import Response


@view_config(route_name='hubInfo', request_method='GET', renderer='website:hubInfo.html')
def getHubInfo(request):
    """TODO: Document this view"""
    outputType = None

    if 'Accept' in request.headers:
        outputType = request.headers['Accept']

    query = request.matchdict
    output = Hubs.getHubInfo(query)

    if 'text/html' in outputType:
        extraLabelInfo = Labels.hubInfoLabels(query)
        output = {'hubInfo': output, 'user': request.authenticated_userid, **extraLabelInfo, 'hubName': query['hub']}
        return output
    elif outputType == 'json' or outputType == 'application/json':
        return Response(json.dumps(output), charset='utf8', content_type='application/json')

    return Response(status=404)


@view_config(route_name='jbrowseJson', request_method='GET')
def getJbrowseJsons(request):
    query = request.matchdict
    query['currentUser'] = request.authenticated_userid

    if 'json' in query['handler']:
        output = json.dumps(Hubs.getHubJsons(query, query['handler']))
        return Response(output,
                        charset='utf8', content_type='application/json')
    else:
        print(query['handler'], 'not yet implemented')
        return Response(status=404)


@view_config(route_name='deleteHub', request_method='DELETE')
def deleteHub(request):
    """Delete a db.HubInfo object

    Using a transaction delete a db.HubInfo by replacing it with a None object

    Redirects
    ---------
    myHubs: reroute to page from which deleting is page so that deleting process of a hub is seamless.
    """
    userid = request.unauthenticated_userid
    owner = request.matchdict['user']
    hub = request.matchdict['hub']

    # create authorization
    Hubs.deleteHub(owner, hub, userid)

    url = request.route_url('myHubs', _app_url=get_app_url(request))
    return HTTPFound(location=url)


@view_config(route_name='uploadHubUrl', request_method='PUT', renderer='json')
def uploadHubUrl(request):
    try:
        data = request.json_body
    except json.decoder.JSONDecodeError:
        data = {**request.params}

    data['user'] = request.authenticated_userid

    output = Hubs.parseHub(data)

    print('uhu out')

    return output


@view_config(route_name='public', request_method='POST')
def setPublic(request):
    """Make a hub public from checking the public checkbox on a hub card

    Update the db.HubInfo object from the post request by receiving its hub name and owner userid and creating a
    transaction to update the 'isPublic' dictionary item in the Hub.

    Redirects
    ---------
    myHubs: the route in which the post request is made from initially so that the process of making a hub public is
        seamless.
    """

    try:
        data = {**request.json_body, **request.matchdict}
    except json.decoder.JSONDecodeError:
        data = {**request.params, **request.matchdict}

    data['currentUser'] = request.authenticated_userid

    Hubs.makeHubPublic(data)

    url = request.route_url('myHubs', _app_url=get_app_url(request))
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

    userid = request.authenticated_userid
    query = request.matchdict
    hubName = query['hub']
    owner = query['user']
    category = request.params['category']
    trackName = request.params['track']
    url = request.params['url']

    Hubs.addTrack(owner, hubName, userid, category, trackName, url)

    url = request.route_url('myHubs', _app_url=get_app_url(request))
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

    userid = request.authenticated_userid
    query = request.matchdict
    hubName = query['hub']
    owner = query['user']
    trackName = request.params['track']

    Hubs.removeTrack(owner, hubName, userid, trackName)

    url = request.route_url('myHubs', _app_url=get_app_url(request))
    return HTTPFound(location=url)

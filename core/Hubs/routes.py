from typing import Optional

from . import Hubs

from core.Labels import Labels
from core.util import PLConfig as cfg

from pydantic import BaseModel
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory='website/templates')


import core


@core.hubRouter.get('/info',
                      responses={
                          200: {
                              "content": {"text/html": {}},
                              "description": "Provides information on a job",
                          }
                      },)
def getHubInfo(request: Request, user: str, hub: str):
    """TODO: Document this view"""
    data = {'user': user, 'hub': hub}

    output = Hubs.getHubInfo(data)

    if 'accept' in request.headers:
        outputType = request.headers['accept']
    else:
        outputType = 'json'

    if 'text/html' in outputType:
        extraLabelInfo = Labels.hubInfoLabels(data)
        output = {'request': request, 'hubInfo': output, **extraLabelInfo, 'hubName': hub, 'user': 'user'}
        return templates.TemplateResponse('hubInfo.html', output)
    elif outputType == 'json' or outputType == 'application/json' or outputType == '*/*':
        return output


@core.hubRouter.get('/data/{handler}', include_in_schema=False)
async def getJbrowseJsons(user: str, hub: str, handler: str):
    # Only really used for parsing the hubInfo into a form which JBrowse can work with
    data = {'user': user, 'hub': hub}

    return Hubs.getHubJsons(data, handler)


@core.hubRouter.delete('')
def deleteHub(request: Request, user: str, hub: str):
    """Delete a db.HubInfo object

    Using a transaction delete a db.HubInfo by replacing it with a None object

    Redirects
    ---------
    myHubs: reroute to page from which deleting is page so that deleting process of a hub is seamless.
    """

    authUser = request.session.get('user')

    if authUser is None:
        userEmail = None
    else:
        userEmail = authUser['email']

    # create authorization
    Hubs.deleteHub(user, hub, userEmail)

    return RedirectResponse(request.url)


class HubURL(BaseModel):
    url: str


@core.otherRouter.put('/uploadHubUrl', tags=['Hubs'])
async def uploadHubUrl(request: Request, hubUrl: HubURL):
    user = request.session.get('user')

    if user is None:
        userEmail = None
    else:
        userEmail = user['email']

    output = Hubs.parseHub(hubUrl, userEmail)

    return output


@core.hubRouter.post('/public')
async def setPublic(request: Request, user: str, hub: str):
    """Make a hub public from checking the public checkbox on a hub card

    Update the db.HubInfo object from the post request by receiving its hub name and owner userid and creating a
    transaction to update the 'isPublic' dictionary item in the Hub.

    Redirects
    ---------
    myHubs: the route in which the post request is made from initially so that the process of making a hub public is
        seamless.
    """

    body = await request.body()

    data = {'user': user, 'hub': hub, 'chkpublic': len(body) != 0}

    authUser = request.session.get('user')

    if authUser is None:
        authUserEmail = 'Public'
    else:
        authUserEmail = authUser['email']

    # TODO: Authentication
    data['currentUser'] = authUserEmail

    returnVal = Hubs.makeHubPublic(data)

    # See other status code, should redirect to GET response instead of POST
    return RedirectResponse('/myHubs', status_code=304)


@core.hubRouter.put('/addTrack')
def addTrack(request: Request, user: str, hub: str, category: str, trackName: str, trackUrl: str):
    """Add a track to a db.HubInfo object

    Update the db.HubInfo object from the post request by receiving its hub name and owner userid and then conducting a
    transaction in which the HubInfo['tracks'] item in the dictionary is updated with a new dict item with trackName as
    a key and the track info as the value.

    Redirects
    ---------
    myHubs: the route in which the post request is made from initially so that the process of adding a track to the
        current hub is seamless.
    """

    authUser = request.session.get('user')

    if authUser is None:
        userEmail = None
    else:
        userEmail = authUser['email']
    
    hubName = hub
    owner = user

    Hubs.addTrack(owner, hubName, userEmail, category, trackName, trackUrl)

    return RedirectResponse('/myHubs')


@core.hubRouter.put('/removeTrack')
def removeTrack(request: Request, user: str, hub: str, trackName: str):
    """Remove a track from a db.HubInfo object

    Update the db.HubInfo object from the post request by receiving its hub name and owner userid and then conducting a
    transaction in which the HubInfo['tracks'] item in the dictionary is updated by removing a dict item of the track
    name.

    Redirects
    ---------
    myHubs: the route in which the post request is made from initially so that the process of removing a track from the
        current hub is seamless.
    """

    authUser = request.session.get('user')

    if authUser is None:
        userEmail = None
    else:
        userEmail = authUser['email']

    Hubs.removeTrack(user, hub, userEmail, trackName)

    return RedirectResponse('/myHubs')


@core.hubRouter.get('/unlabeled')
def getUnlabeledRegion(request: Request, user: str, hub: str):
    query = {'user': user, 'hub': hub, 'type': 'unlabeled'}

    return Hubs.goToRegion(query)


@core.hubRouter.get('/labeled')
def getLabeledRegion(request: Request, user: str, hub: str):
    query = {'user': user, 'hub': hub, 'type': 'labeled'}

    return Hubs.goToRegion(query)

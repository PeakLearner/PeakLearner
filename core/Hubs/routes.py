
from typing import Optional

from . import Hubs, Models

from core.Labels import Labels
from core.util import PLConfig as cfg

from pydantic import BaseModel
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory='website/templates')

import core


@core.hubRouter.get('/', response_class=HTMLResponse)
def getJbrowsePage(request: Request, user: str, hub: str):
    user = request.session.get('user')
    picture = None

    if user is None:
        user = 'Public'
    else:
        print(user)
        picture = user['picture']
        user = user['email']

    return templates.TemplateResponse('jbrowse.html', {'request': request, 'user': user, 'picture': picture})


@core.hubRouter.get('/info',
                    responses={
                        200: {
                            "content": {"text/html": {}},
                            "description": "Provides information on a hub",
                        }
                    },
                    response_model=Models.HubInfo,
                    summary='Get the hubInfo for this hub',
                    description='Gets the hubInfo for this hub. It contains the tracks, urls, the reference genome, and categories for that data')
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


@core.hubRouter.delete('',
                       summary='Deletes a hub, requires authentication',
                       description='Removes a hub from the database. The labels/models aren\'t deleted')
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


@core.otherRouter.put('/uploadHubUrl', tags=['Hubs'],
                      summary='Upload a new hub.txt to the system',
                      description='Route for uploading a new UCSC formatted hub.txt with a genomes.txt and trackList.txt in the same directory')
async def uploadHubUrl(request: Request, hubUrl: HubURL):
    user = request.session.get('user')

    if user is None:
        userEmail = None
    else:
        userEmail = user['email']

    output = Hubs.parseHub(hubUrl, userEmail)

    return output


@core.hubRouter.post('/public',
                     summary='Sets a hub to a public hub',
                     description='Allows a hub to be publicly viewed')
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


@core.hubRouter.post('/addTrack',
                    summary='Adds a track to a hub',
                    description='Adds a track to a hub with a track name and categories')
def addTrack(request: Request, user: str, hub: str, category: str = Form(...), track: str = Form(...), url: str = Form(...)):
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

    Hubs.addTrack(owner, hubName, userEmail, category, track, url)

    return RedirectResponse('/myHubs', status_code=302)


@core.hubRouter.post('/removeTrack',
                    summary='Removes a track from a hub',
                    description='Removes a track from a hub with a track name. This could be changed to a DELETE')
async def removeTrack(request: Request, user: str, hub: str, trackName: str = Form(...)):
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

    return RedirectResponse('/myHubs', status_code=302)


@core.hubRouter.get('/unlabeled',
                    summary='Gets an unlabeled region for the hub',
                    description='Gets an unlabeled region for the hub, and returns what is needed to navigate to that')
async def getUnlabeledRegion(request: Request, user: str, hub: str):
    query = {'user': user, 'hub': hub, 'type': 'unlabeled'}

    return Hubs.goToRegion(query)


@core.hubRouter.get('/labeled',
                    summary='Gets a labeled region for the hub',
                    description='Gets a labeled region for the hub, and returns what is needed to navigate to that')
async def getLabeledRegion(request: Request, user: str, hub: str):
    query = {'user': user, 'hub': hub, 'type': 'labeled'}

    return Hubs.goToRegion(query)

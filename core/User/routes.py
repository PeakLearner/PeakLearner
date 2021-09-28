import json
from typing import Optional, List

from pydantic.main import BaseModel
from . import User
import core
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import Response, HTMLResponse, RedirectResponse

templates = Jinja2Templates(directory='website/templates')


@core.otherRouter.get('/profile')
def getUserProfile(request: Request):
    authUser = request.session.get('user')

    if authUser is None:
        return Response(status_code=401)

    userName = authUser['name']
    userPicture = authUser['picture']
    authUser = authUser['email']

    out = User.populateUserProfile(authUser)

    return templates.TemplateResponse('profile.html', {'request': request,
                                                       'user': authUser,
                                                       'name': userName,
                                                       'picture': userPicture,
                                                       'hubLabelStats': out})

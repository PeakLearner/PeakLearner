import json
from typing import Optional, List

from pydantic.main import BaseModel
from . import User
import core
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import Response, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

templates = Jinja2Templates(directory='website/templates')


@core.otherRouter.get('/profile')
def getUserProfile(request: Request, db: Session = Depends(core.get_db)):
    authUser = request.session.get('user')

    if authUser is None:
        return Response(status_code=401)

    userName = authUser['name']
    userPicture = authUser['picture']
    db.commit()
    authUser = User.getAuthUser(request, db)
    db.commit()

    out = User.populateUserProfile(db, authUser)

    return templates.TemplateResponse('profile.html', {'request': request,
                                                       'user': authUser.name,
                                                       'name': userName,
                                                       'picture': userPicture,
                                                       'hubLabelStats': out})

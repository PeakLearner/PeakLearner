import json
from typing import Optional

import core
from core.Hubs import Hubs
from sqlalchemy.orm import Session
from core.Permissions import Permissions
from core.User import User
from fastapi import Request, Form, Depends
from fastapi.responses import Response, RedirectResponse


@core.hubRouter.post('/permissions')
async def adjustPermsPOST(request: Request,
                          user: str,
                          hub: str,
                          coUser: Optional[str] = Form(...),
                          Label: Optional[str] = Form(None),
                          Track: Optional[str] = Form(None),
                          Hub: Optional[str] = Form(None),
                          Moderator: Optional[str] = Form(None),
                          db: Session = Depends(core.get_db)):
    """Process permission change post requests

    Update the db.HubInfo object from the post request by receiving its hub name, owner userid and the userid of which
    permissions are being changed. Then a transaction is started to update the permissions related to those three
    parameters and updating the permissions to match the post requests inputted changes.

    Redirects
    ---------
    myHubs: the route in which the post request is made from initially so that the process changing hub permissions is
        seamless.
    """

    perms = {'Label': Label,
             'Track': Track,
             'Hub': Hub,
             'Moderator': Moderator}

    args = {'coUser': coUser}

    for key in perms.keys():
        if perms[key] is not None:
            args[key] = perms[key]

    db.commit()
    authUser = User.getAuthUser(request, db)
    db.commit()

    Permissions.adjustPermissions(db, user, hub, authUser, args)
    db.commit()

    return RedirectResponse('/myHubs', status_code=302)


@core.hubRouter.post('/addUser')
async def addUser(request: Request, user: str, hub: str, userEmail: str = Form(...),
                  db: Session = Depends(core.get_db)):
    """Add a user to a db.HubInfo object

    Update the db.HubInfo object from the post request by receiving its hub name and owner userid and then calling the
    addUserToHub function to add that user to the current hub and then refresh the page to reflect that addition.

    Redirects
    ---------
    myHubs: the route in which the post request is made from initially so that the process of adding a user to the
        current hub is seamless.
    """
    db.commit()
    authUser = User.getAuthUser(request, db)
    db.commit()

    out = Permissions.addUserToHub(db, user, hub, authUser, userEmail)
    if out is not None:
        return out
    db.commit()

    return RedirectResponse('/myHubs', status_code=302)


@core.hubRouter.post('/removeUser')
async def removeUser(request: Request, user: str, hub: str, coUserName: str = Form(...),
                     db: Session = Depends(core.get_db)):
    """Remove a user to a db.HubInfo object

    Update the db.HubInfo object from the post request by receiving its hub name and owner userid and then calling the
    removeUserFromHub function to remove that user from the hub, then refreshing the page to reflect that deletion.

    Redirects
    ---------
    myHubs: the route in which the post request is made from initially so that the process of removing a user from the
        current hub is seamless.
    """

    db.commit()
    authUser = User.getAuthUser(request, db)
    db.commit()

    out = Hubs.removeUserFromHub(db, user, hub, authUser, coUserName)
    if out is not None:
        return out

    db.commit()

    return RedirectResponse('/myHubs', status_code=302)

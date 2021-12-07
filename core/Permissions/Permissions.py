from fastapi.security import OAuth2PasswordBearer
from fastapi import Response
from core import models, dbutil
from sqlalchemy.orm import Session
from core.User import User


defaultPerms = {'Label': True, 'Track': False, 'Hub': False, 'Moderator': False}


def hasViewPermission(hub, authUser):
    if hub.public:
        return True

    userPerms = hub.permissions.filter(models.HubPermission.user == authUser.id).first()

    if userPerms is None:
        if hub.owner == authUser.id:
            return True
        return False
    return True


def getHubPermissions(db: Session, hub):
    perms = hub.permissions.all()
    output = {}

    for perm in perms:
        permUser = db.query(models.User).filter(models.User.id == perm.user).first()
        output[permUser.name] = perm.getPermsDict()

    return output


def adjustPermissions(db: Session, owner, hub, authUser, args):
    owner, hub = dbutil.getHub(db, owner, hub)

    if hub is None:
        return Response(status_code=404)
    if not hub.checkPermission(authUser, 'Moderator'):
        return Response(status_code=403)

    out = hub.updatePerms(db, args)

    if out is None:
        return Response(status_code=403)

    hub.permissions.append(out)
    db.flush()
    db.refresh(out)


def addUserToHub(db, owner, hubName, authUser, newUser):
    """Adds a user to a hub given the hub name, owner userid, and the userid of the user to be added
    Adjusts the db.HubInfo object by adding the new user to the ['users'] dict item in the db object.
    Additionally the permissions of that user are initialized to being empty.
    """

    user, hub = dbutil.getHub(db, owner, hubName)

    if hub is None:
        return Response(status_code=404)

    if not hub.checkPermission(authUser, 'hub'):
        return Response(status_code=401)

    userToAdd = User.getUser(newUser, db)

    perm = hub.permissions.filter(models.HubPermission.user == userToAdd.id).first()

    if perm is None:
        perm = models.HubPermission(hubId=hub.id,
                                    user=userToAdd.id,
                                    label=defaultPerms['Label'],
                                    track=defaultPerms['Track'],
                                    hub=defaultPerms['Hub'],
                                    moderator=defaultPerms['Moderator'])
        hub.permissions.append(perm)
        db.flush()
        db.refresh(perm)
    else:
        return Response(status_code=400)

    # TODO: Perhaps send an email to the user which was added?

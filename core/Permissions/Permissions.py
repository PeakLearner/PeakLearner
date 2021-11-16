from simpleBDB import retry, txnAbortOnError, AbortTXNException
from core.util import PLdb as db
from fastapi.security import OAuth2PasswordBearer
from fastapi import Response
from core import models
from sqlalchemy.orm import Session


defaultPerms = {'Label': True, 'Track': False, 'Hub': False, 'Moderator': False}


class Permission:

    def __init__(self, user, hub):
        self.owner = str(user)
        self.hub = hub
        self.users = {'Public': {'Label': True, 'Track': False, 'Hub': False, 'Moderator': False}}
        self.groups = {}

    @classmethod
    def fromStorable(cls, storable):
        """Create a permissions object from a storable object

        These storables are dicts which are stored using the Job type in api.util.PLdb
        """

        # https://stackoverflow.com/questions/2168964/how-to-create-a-class-instance-without-calling-initializer

        try:
            self = cls.__new__(cls)
            self.owner = str(storable['owner'])
            self.hub = storable['hub']
            self.users = storable['users']
            self.groups = storable['groups']
            return self
        except TypeError:
            return storable

    def putNewPermissions(self):
        txn = db.getTxn()
        self.putPermissionsWithTxn(txn=txn)
        txn.commit()

    def putPermissionsWithTxn(self, txn=None):
        db.Permission(self.owner, self.hub).put(self.__dict__(), txn=txn)

    def hasPermission(self, userToCheck, perm):
        if self.owner == userToCheck:
            return True

        if userToCheck is not None and userToCheck in self.users.keys():
            userKey = userToCheck
        else:
            userKey = 'Public'

        currentPerms = self.users[userKey]

        if currentPerms['Moderator']:
            return True

        return currentPerms[perm]

    def adjustPermissions(self, owner, hub, userid, coUser, args, txn=None):

        if not self.hasPermission(userid, 'Moderator'):
            raise AbortTXNException

        if coUser in self.users:
            userPerms = self.users[coUser]

            for perm in userPerms.keys():
                if perm in args:
                    userPerms[perm] = True
                else:
                    userPerms[perm] = False

    def __dict__(self):
        output = {
            'owner': self.owner,
            'hub': self.hub,
            'users': self.users,
            'groups': self.groups
        }

        return output


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
        print(permUser)
    return output


def adjustPermissions(owner, hub, userid, args, txn=None):
    # create authorization
    permDb = db.Permission(owner, hub)
    perms = permDb.get(txn=txn, write=True)
    coUser = args['coUser']
    perms.adjustPermissions(owner, hub, userid, coUser, args, txn=txn)
    permDb.put(perms, txn=txn)
    return True


@retry
@txnAbortOnError
def addUserToHub(request, owner, hubName, newUser, txn=None):
    """Adds a user to a hub given the hub name, owner userid, and the userid of the user to be added
    Adjusts the db.HubInfo object by adding the new user to the ['users'] dict item in the db object.
    Additionally the permissions of that user are initialized to being empty.
    """

    authUser = request.session.get('user')

    if authUser is None:
        authUser = 'Public'
    else:
        authUser = authUser['email']

    permDb = db.Permission(owner, hubName)
    perms = permDb.get(txn=txn, write=True)

    if perms is None:
        return Response(status_code=404)

    if not perms.hasPermission(authUser, 'Hub'):
        return Response(status_code=401)

    perms.users[newUser] = defaultPerms.copy()

    permDb.put(perms, txn=txn)

    # TODO: Perhaps send an email to the user which was added?


@retry
@txnAbortOnError
def hasAdmin(user, txn=None):
    if user == 'Public':
        return False
    permDb = db.Permission('All', 'Admin')
    perms = db.db.Resource.get(permDb, txn=txn, write=True)

    if perms is None:
        db.db.Resource.put(permDb, [user], txn=txn)
        return True

    if isinstance(perms, list):
        if user in perms:
            return True

    return False


@retry
@txnAbortOnError
def addAdmin(user, txn=None):
    if user == 'Public':
        return 'Can\'t add Public as admin'
    permDb = db.Permission('All', 'Admin')
    perms = db.db.Resource.get(permDb, txn=txn, write=True)

    if perms is None:
        db.db.Resource.put(permDb, [user], txn=txn)

    elif isinstance(perms, list):
        if user not in perms:
            perms.append(user)
            db.db.Resource.put(permDb, perms, txn=txn)
        else:
            return '%s is already an admin' % user

    return '%s added as admin' % user


oauth2_scheme = OAuth2PasswordBearer(tokenUrl='test')

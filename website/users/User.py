from pyramid.security import Allow
import uuid

# DEFINE MEMBER MODEL
class User(object):
    @property
    def __acl__(self):
        return [
            (Allow, self.uid, 'view'),
        ]

    def __init__(self, username, password, groups=None):
        self.uid = uuid.uuid4()
        self.username = username
        self.password = password
        self.groups = groups or []

    def check_password(self, passwd):
        return self.password == passwd

    def __str__(self):
        return "{self.uid}".format(self=self)
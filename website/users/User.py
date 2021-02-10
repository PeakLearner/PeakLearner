from pyramid.security import Allow

# DEFINE MEMBER MODEL
class User(object):
    @property
    def __acl__(self):
        return [
            (Allow, self.login, 'view'),
        ]

    def __init__(self, login, password, groups=None):
        self.login = login
        self.password = password
        self.groups = groups or []

    def check_password(self, passwd):
        return self.password == passwd
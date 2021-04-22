from pyramid.config import Configurator
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.security import ALL_PERMISSIONS
from pyramid.security import Allow
from website.users.Users import USERS


class RootFactory(object):
    """ replace default factory to give default permissions to users """

    __acl__ = [
        (Allow, 'g:admin', ALL_PERMISSIONS),
    ]

    def __init__(self, request):
        self.request = request


class UserFactory(object):
    """ routes accessing user object must use this factory """

    __acl__ = [
        (Allow, 'g:admin', ALL_PERMISSIONS),
    ]

    def __init__(self, request):
        self.request = request

    def __getitem__(self, key):
        user = USERS[key]
        user.__parent__ = self
        user.__name__ = key
        return user


def group_finder(userid, request):
    """ returns groups of a given userid in USERS """

    user = USERS.get(userid)
    if user:
        return ['g:%s' % g for g in user.groups]


def main(global_config, **settings):
    """ run configurator for PeakLearner """

    config = Configurator(settings=settings)

    # create authentication and authorization policies
    authn_policy = AuthTktAuthenticationPolicy(
        config.get_settings()['security.google_login.client_secret'],
        callback=group_finder,
    )
    authz_policy = ACLAuthorizationPolicy()

    # set config settings
    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)
    config.set_root_factory(RootFactory)

    # Front end page
    config.add_route('home', '')
    config.add_route('about', '/about/')
    config.add_route('jbrowse', '/jbrowse/')
    config.add_route('newHub', '/newHub/')
    config.add_route('tutorial', '/tutorial/')
    config.add_route('backup', '/backup/')
    config.add_route('stats', '/stats/')
    config.add_route('modelStats', '/stats/model/')
    config.add_route('labelStats', '/stats/label/')
    config.add_route('jobStats', '/stats/job/')
    config.add_static_view(name='assets', path='website:static/assets')
    config.add_route('addUser', '/addUser/')
    config.add_route('hubRemoveUser', '/hubRemoveUser/')
    config.add_route('addTrack', '/addTrack/{user}/{hub}/')
    config.add_route('removeTrack', '/removeTrack/{user}/{hub}/')
    config.add_route('adjustPerms', '/adjustPerms/{user}/{hub}/{couser}')
    config.add_route('public', '/public/{user}/{hub}/')
    config.add_route('myHubs', '/myHubs/')
    config.add_route('publicHubs', '/publicHubs/')
    config.add_route('moreHubInfo', '/myHubs/{hub}/moreInfo/')
    config.add_route('uploadHubUrl', '/uploadHubUrl/')
    config.add_route('jobs', '/jobs/')
    config.add_route('jobInfo', '/jobs/info/')

    # rendering related configurations
    config.include('pyramid_jinja2')
    config.include('pyramid_google_login')  # library for google oauth
    config.add_static_view(name='tutorial/static', path='website:static/tutorial')
    config.add_static_view(name='about', path='website:static/about')
    config.add_static_view(name='myHubs/static', path='api:static/')
    config.add_jinja2_renderer('.html')
    config.scan('website.views')

    # account routes
    config.add_route('login', '/login/')
    config.add_route('failed', '/failed/')
    config.add_route('authenticate', '/authenticate/')
    config.add_route('logout', '/logout/')
    config.add_route('api', '/api/')
    config.add_route('doBackup', '/doBackup/')
    config.add_route('doRestore', '/doRestore/')
    config.add_route('prediction', '/prediction/')
    config.add_route('hubInfo', '/{user}/{hub}/info/')
    config.add_route('hubData', '/{user}/{hub}/data/{handler}')
    config.add_route('trackData', '/{user}/{hub}/{track}/{handler}/')
    config.add_static_view(name='/{user}/{hub}', path='jbrowse:jbrowse')
    config.add_route('deleteHub', '/deleteHub/')
    config.scan('api.views')

    return config.make_wsgi_app()

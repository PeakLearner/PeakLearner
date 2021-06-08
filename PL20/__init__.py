import os
from pyramid.config import Configurator
from pyramid.events import NewResponse, subscriber


@subscriber(NewResponse)
def add_cors_headers(event):
    if event.request.is_xhr:
        event.response.headers.update({
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
        })


def main(global_config, **settings):
    """Prepare a Pyramid app."""
    config = Configurator(settings=settings)

    # Front end page
    config.add_route('home', '')
    config.add_route('about', '/about/')
    config.add_route('newHub', '/newHub/')
    config.add_route('tutorial', '/tutorial/')
    config.add_route('backup', '/backup/')
    config.add_route('stats', '/stats/')
    config.add_route('modelStats', '/stats/model/')
    config.add_route('labelStats', '/stats/label/')
    config.add_static_view(name='assets', path='website:static/assets')
    config.add_route('addUser', '/addUser/')
    config.add_route('hubRemoveUser', '/hubRemoveUser/')
    config.add_route('addTrack', '/addTrack/{user}/{hub}/')
    config.add_route('removeTrack', '/removeTrack/{user}/{hub}/')
    config.add_route('adjustPerms', '/adjustPerms/{user}/{hub}/{coUser}')
    config.add_route('public', '/public/{user}/{hub}/')
    config.add_route('myHubs', '/myHubs/')
    config.add_route('moreHubInfo', '/myHubs/{owner}/{hub}/moreInfo/')
    config.add_route('jobsStats', '/stats/job/')
    config.add_route('jobStats', '/stats/job/{id}/')
    config.add_route('uploadHubUrl', '/uploadHubUrl/')
    config.add_route('jobs', '/jobs/')
    config.add_route('jobInfo', '/jobs/info/')
    config.add_route('help', '/help/')
    config.add_route('api', '/api/')
    config.add_route('login', '/login/')
    config.add_route('failed', '/failed/')
    config.add_route('authenticate', '/authenticate/')
    config.add_route('logout', '/logout/')

    # rendering related configurations
    config.include('pyramid_jinja2')
    config.include('pyramid_google_login')  # library for google oauth
    config.add_static_view(name='tutorial/static', path='website:static/tutorial')
    config.add_static_view(name='about', path='website:static/about')
    config.add_static_view(name='myHubs/static', path='api:static/')
    config.add_jinja2_renderer('.html')
    config.scan('website.views')

    config.include("pyramid_openapi3")
    config.add_static_view(name="spec", path="spec")
    config.pyramid_openapi3_spec_directory(os.path.join(os.path.dirname(__file__), "spec/openapi.yaml"))
    config.pyramid_openapi3_add_explorer()
    config.add_route('hubInfo', '/{user}/{hub}/info/')

    config.add_route('hubLabels', '/{user}/{hub}/labels/')
    config.add_route('trackLabels', '/{user}/{hub}/{track}/labels/')
    config.scan('core.Labels.views')

    config.add_route('hubModels', '/{user}/{hub}/models/')
    config.add_route('trackModels', '/{user}/{hub}/{track}/models/')
    config.scan('core.Models.views')

    config.add_route('jbrowseJson', '/{user}/{hub}/data/{handler}')
    config.scan('core.Hubs.views')
    config.add_static_view(name='/{user}/{hub}', path='jbrowse:jbrowse')


    from wsgicors import CORS
    return CORS(config.make_wsgi_app(), headers="*", methods="*", maxage="180", origin="*")

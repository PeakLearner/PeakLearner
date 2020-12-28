from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from api.util import PLConfig as cfg


http_server = None


def startServer():
    global http_server
    with Configurator() as config:
        config.add_route('home', '')
        config.add_route('about', '/about/')
        config.add_route('jbrowse', '/jbrowse/')
        config.add_route('newHub', '/newHub/')
        config.add_route('uploadHubUrl', '/uploadHubUrl/')
        config.add_route('jobs', '/jobs/')
        config.add_route('jobInfo', '/jobs/info/')
        config.add_route('api', '/api/')
        config.add_route('hubInfo', '/{user}/{hub}/info/')
        config.add_route('hubData', '/{user}/{hub}/data/{handler}')
        config.add_route('trackData', '/{user}/{hub}/{track}/{handler}/')
        config.add_static_view(name='/{user}/{hub}', path='jbrowse')
        config.include('pyramid_jinja2')
        config.add_jinja2_renderer('.html')
        config.scan('website.views')
        config.scan('api.views')
        app = config.make_wsgi_app()
    http_server = make_server('0.0.0.0', cfg.httpServerPort, app)
    http_server.serve_forever()


def shutdownServer():
    print('Shutting down PeakLearner')
    if http_server is not None:
        http_server.shutdown()

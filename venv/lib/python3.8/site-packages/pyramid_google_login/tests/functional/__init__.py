import unittest

from pyramid.config import Configurator
from pyramid.decorator import reify
from pyramid.request import Request
from pyramid.scripting import prepare
from webtest import TestApp

from pyramid_google_login.utility import IApiClientFactory


class Base(unittest.TestCase):

    settings = {
        'security.google_login.client_id': 'client id',
        'security.google_login.client_secret': 'client secret',
        'security.google_login.access_type': 'offline',
        'security.google_login.hosted_domain': 'bob.com',
        }

    @reify
    def config(self):
        self.addCleanup(delattr, self, 'config')
        _config = Configurator(settings=self.settings)
        _config.include('pyramid_google_login')
        return _config

    @reify
    def app(self):
        self.addCleanup(delattr, self, 'app')
        return TestApp(self.config.make_wsgi_app())

    def get_request(self, path='/'):
        self.app  # to bootstrap env
        request = Request.blank(path)
        env = prepare(request=request, registry=self.config.registry)
        self.addCleanup(env['closer'])
        return request


class ApiMockBase(Base):

    @reify
    def config(self):
        _config = super(ApiMockBase, self).config
        _config.commit()
        _config.include('pyramid_google_login.tests')
        return _config

    @reify
    def googleapi(self):
        return self.config.registry.getUtility(IApiClientFactory)

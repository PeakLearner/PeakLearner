import unittest

import mock


def mock_request():
    request = mock.Mock()
    request.route_url = mock.Mock()
    request.route_url.return_value = '/'
    return request


class TestHelpers(unittest.TestCase):

    def test_redirect_to_signin(self):
        from pyramid.httpexceptions import HTTPFound
        from pyramid_google_login import redirect_to_signin

        request = mock_request()

        httpfound = redirect_to_signin(request)
        self.assertIsInstance(httpfound, HTTPFound)

        request.route_url.assert_called_once_with('auth_signin', _query={})
        self.assertEqual(httpfound.location, request.route_url.return_value)

    def test_redirect_to_signin_url(self):
        from pyramid.httpexceptions import HTTPFound
        from pyramid_google_login import redirect_to_signin

        request = mock_request()

        httpfound = redirect_to_signin(request, url='/test')
        self.assertIsInstance(httpfound, HTTPFound)

        request.route_url.assert_called_once_with('auth_signin',
                                                  _query={'url': '/test'})
        self.assertEqual(httpfound.location, request.route_url.return_value)

    def test_redirect_to_signin_headers(self):
        from pyramid.httpexceptions import HTTPFound
        from pyramid_google_login import redirect_to_signin

        request = mock_request()

        test_header = ('X-Test', 'Yeap')

        httpfound = redirect_to_signin(request, headers=[test_header])
        self.assertIsInstance(httpfound, HTTPFound)

        self.assertEqual(httpfound.location, request.route_url.return_value)
        self.assertIn(test_header, httpfound.headerlist)

    def test_find_landing_path(self):
        from pyramid_google_login import find_landing_path

        request = mock_request()
        request.registry.settings = {

        }

        path = find_landing_path(request)

        self.assertEqual(path, '/')

    def test_find_landing_path_landing_url(self):
        from pyramid_google_login import find_landing_path

        request = mock_request()
        request.registry.settings = {
            'security.google_login.landing_url': '/foobar',
        }

        path = find_landing_path(request)

        self.assertEqual(path, '/foobar')

    def test_find_landing_path_landing_route(self):
        from pyramid_google_login import find_landing_path

        request = mock_request()
        request.registry.settings = {
            'security.google_login.landing_route': 'myroute',
        }

        path = find_landing_path(request)

        self.assertEqual(path, request.route_path.return_value)

    def test_find_landing_path_landing_route_static(self):
        from pyramid_google_login import find_landing_path

        request = mock_request()
        request.registry.settings = {
            'security.google_login.landing_route': 'myroute',
        }
        request.route_path.side_effect = KeyError()

        path = find_landing_path(request)

        self.assertEqual(path, request.static_path.return_value)

    def test_find_landing_path_fallback(self):
        from pyramid_google_login import find_landing_path

        request = mock_request()
        request.registry.settings = {
            'security.google_login.landing_route': 'myroute',
        }
        request.route_path.side_effect = KeyError()
        request.static_path.side_effect = KeyError()

        path = find_landing_path(request)

        self.assertEqual(path, '/')

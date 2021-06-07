import mock

from pyramid_google_login.utility import IApiClientFactory


def includeme(config):
    dummy_api_client = mock.MagicMock()

    config.registry.registerUtility(dummy_api_client,
                                    provided=IApiClientFactory)
    config.add_request_method(new_dummy_api_client, 'googleapi', reify=True)


def new_dummy_api_client(request):
    return request.registry.getUtility(IApiClientFactory)

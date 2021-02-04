from pyramid.view import view_config
from api.util import PLdb as db


@view_config(route_name='home', renderer='index.html')
def home(request):
    return {}


@view_config(route_name='about', renderer='about.html')
def about(request):
    return {}


@view_config(route_name='newHub', renderer='newHub.html')
def newHub(request):
    return {}


@view_config(route_name='tutorial', renderer='tutorial.html')
def tutorial(request):
    return {}


@view_config(route_name='backup', renderer='backup.html')
def backup(request):
    return {'last_backup': db.getLastBackup(),
            'backups': db.getAvailableBackups()}


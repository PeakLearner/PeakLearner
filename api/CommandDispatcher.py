from api.Handlers import LabelHandler, ModelHandler, JobHandler
from api import PLdb as db


def jsonInput(data):
    command = data['command']
    # for some reason data['args'] is a list containing a dict
    args = data['args']
    commandOutput = commands(command)(args)

    return commandOutput


def commands(command):
    command_list = {
        'addLabel': LabelHandler.addLabel,
        'removeLabel': LabelHandler.removeLabel,
        'updateLabel': LabelHandler.updateLabel,
        'getLabels': LabelHandler.getLabels,
        'parseHub': LabelHandler.parseHub,
        'getProblems': LabelHandler.getProblems,
        'getGenome': LabelHandler.getGenome,
        'getTrackUrl': LabelHandler.getTrackUrl,
        'getJob': JobHandler.getJob,
        'updateJob': JobHandler.updateJob,
        'removeJob': JobHandler.removeJob,
        'getAllJobs': JobHandler.getAllJobs,
        'getModel': ModelHandler.getModel,
        'getModelSummary': ModelHandler.getModelSummary,
        'putModel': ModelHandler.putModel,
    }

    return command_list.get(command, None)

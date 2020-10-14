import os
import json
import api.HubParse as hubParse
import api.UCSCtoPeakLearner as UCSCtoPeakLearner
import api.PLConfig as cfg
import api.JobHandler as jh
import api.ModelHandler as mh


def jsonInput(data):
    command = data['command']
    # for some reason data['args'] is a list containing a dict
    args = data['args']

    commandOutput = commands(command)(args)

    return commandOutput


def commands(command):
    command_list = {
        'addLabel': addLabel,
        'removeLabel': removeLabel,
        'updateLabel': updateLabel,
        'getLabels': getLabels,
        'parseHub': parseHub,
        'getProblems': getProblems,
        'getGenome': getGenome,
        'getHubInfo': getHubInfo,
        'getJob': jh.getJob,
        'updateJob': jh.updateJob,
        'removeJob': jh.removeJob,
        'getAllJobs': jh.getAllJobs,
        'getModel': mh.getModel,
    }

    return command_list.get(command, None)


# Adds Label to label file
def addLabel(data):
    rel_path = '%s%s_Labels.bedGraph' % (cfg.dataPath, data['name'])

    file_output = []

    default_val = 'unknown'

    added = False

    line_to_append = '%s\t%d\t%d\t%s\n' % (data['ref'], data['start'], data['end'], default_val)

    if not os.path.exists(rel_path):
        with open(rel_path, 'w') as new:
            print("New label file created at %s" % rel_path)
            new.write(line_to_append)
            return data

    # read labels in besides one to delete
    with open(rel_path, 'r') as f:

        current_line = f.readline()

        while not current_line == '':
            lineVals = current_line.split()

            current_line_ref = lineVals[0]
            current_line_start = int(lineVals[1])

            if not added and not (current_line_ref < data['ref'] or current_line_start < data['start']):
                file_output.append(line_to_append)
                added = True

            file_output.append(current_line)
            current_line = f.readline()

        if not added:
            file_output.append(line_to_append)

    # this could be "runtime expensive" saving here instead of just sending label data to the model itself for
    # storage
    with open(rel_path, 'w') as f:
        f.writelines(file_output)

    mh.newLabel(data)

    return data


# Removes label from label file
def removeLabel(data):
    rel_path = '%s%s_Labels.bedGraph' % (cfg.dataPath, data['name'])

    output = []

    line_to_check = '%s\t%s\t%s' % (data['ref'], str(data['start']), str(data['end']))

    # read labels in besides one to delete
    with open(rel_path, 'r') as f:

        current_line = f.readline()

        while not current_line == '':

            if current_line.find(line_to_check) == -1:
                output.append(current_line)

            current_line = f.readline()

    # write labels after one to delete is gone
    with open(rel_path, 'w') as f:
        f.writelines(output)

    mh.deleteLabel(data)

    return data


def updateLabel(data):
    rel_path = '%s%s_Labels.bedGraph' % (cfg.dataPath, data['name'])

    output = []

    line_to_check = '%s\t%s\t%s' % (data['ref'], str(data['start']), str(data['end']))

    # read labels in besides one to delete
    with open(rel_path, 'r') as f:

        current_line = f.readline()

        while not current_line == '':

            if not current_line.find(line_to_check) <= -1:
                output.append('%s\t%s\n' % (line_to_check, data['label']))
            else:
                output.append(current_line)

            current_line = f.readline()

    # write labels after one to delete is gone
    with open(rel_path, 'w') as f:
        f.writelines(output)

    mh.updateModels(data)

    return data


def getLabels(data):
    rel_path = '%s%s_Labels.bedGraph' % (cfg.dataPath, data['name'])
    refseq = data['ref']
    start = data['start']
    end = data['end']

    output = []

    if not os.path.exists(rel_path):
        return output

    with open(rel_path, 'r') as f:

        current_line = f.readline()

        while not current_line == '':
            lineVals = current_line.split()

            lineStart = int(lineVals[1])

            lineEnd = int(lineVals[2])

            if lineVals[0] == refseq:

                lineIfStartIn = (lineStart >= start) and (lineStart <= end)
                lineIfEndIn = (lineEnd >= start) and (lineEnd <= end)
                wrap = (lineStart < start) and (lineEnd > end)

                if lineIfStartIn or lineIfEndIn or wrap:
                    output.append({"ref": refseq, "start": lineStart,
                                   "end": lineEnd, "label": lineVals[3]})

            current_line = f.readline()

    return output


def parseHub(data):
    hub = hubParse.parse(data)
    # Add a way to configure hub here somehow instead of just loading everything
    jh.addJob({'hub': hub['hub']})
    return UCSCtoPeakLearner.convert(hub)


def getProblems(data):
    if 'genome' not in data:
        return

    rel_path = '%sgenomes/%s/%s' % (cfg.dataPath, data['genome'], 'problems.bed')
    refseq = data['ref']
    start = data['start']
    end = data['end']

    output = []

    if not os.path.exists(rel_path):
        return output

    with open(rel_path, 'r') as f:

        current_line = f.readline()

        while not current_line == '':
            lineVals = current_line.split()

            lineStart = int(lineVals[1])

            lineEnd = int(lineVals[2])

            if lineVals[0] == refseq:

                lineIfStartIn = (lineStart >= start) and (lineStart <= end)
                lineIfEndIn = (lineEnd >= start) and (lineEnd <= end)
                wrap = (lineStart < start) and (lineEnd > end)

                if lineIfStartIn or lineIfEndIn or wrap:
                    output.append({"ref": refseq, "start": lineStart,
                                   "end": lineEnd})

            current_line = f.readline()

    return output


def getGenome(data):
    if 'hub' not in data:
        return

    dirs = data['hub'].split('/')

    hub = dirs[0]

    trackListPath = '%s%s/trackList.json' % (cfg.dataPath, hub)

    with open(trackListPath, 'r') as f:
        trackList = json.load(f)

        genomePath = trackList['include'][0].split('/')

        genome = genomePath[-2]

        return genome


def getHubInfo(data):
    if 'hub' not in data:
        return

    genome = getGenome(data)

    genomePath = '%sgenomes/%s' % (cfg.dataPath, genome)

    trackListPath = '%s%s/trackList.json' % (cfg.dataPath, data['hub'])

    output = {'hub': data['hub'], 'genomePath': genomePath, 'tracks': []}

    with open(trackListPath, 'r') as f:
        trackList = json.load(f)

        for track in trackList['tracks']:
            trackLabel = track['label']
            url = track['urlTemplates'][0]['url']

            output['tracks'].append({'name': trackLabel, 'coverage': url})

        return output

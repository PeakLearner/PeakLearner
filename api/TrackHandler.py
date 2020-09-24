import os
import sys
import api.HubParse as hubParse
import api.UCSCtoPeakLearner as UCSCtoPeakLearner
import api.PLConfig as cfg
import api.JobHandler as jh


def jsonInput(data):
    command = data['command']
    # for some reason data['args'] is a list containing a dict
    args = data['args']

    commandOutput = commands(command)(args)

    return commandOutput


def commands(command):
    command_list = {
        'add': addLabel,
        'remove': removeLabel,
        'update': updateLabel,
        'getLabels': getLabels,
        'getModel': getModel,
        'parseHub': parseHub,
        'getJob': jh.getJob,
        'updateJob': jh.updateJob,
        'removeJob': jh.removeJob,
    }

    return command_list.get(command, None)


# Adds Label to label file
def addLabel(data):
    script_dir = os.path.abspath(os.path.dirname(sys.argv[0]))  # <-- absolute dir the script is in
    rel_path = cfg.dataPath + data['name'] + '_Labels.bedGraph'
    abs_path = os.path.join(script_dir, rel_path)

    file_output = []

    default_val = 'unknown'

    added = False

    line_to_append = data['ref'] + ' ' + str(data['start']) + ' ' + str(data['end']) + ' ' + default_val + '\n'

    if not os.path.exists(abs_path):
        with open(abs_path, 'w') as new:
            print("New label file created at %s" % abs_path)
            new.write(line_to_append)
            return data

    # read labels in besides one to delete
    with open(abs_path, 'r') as f:

        current_line = f.readline()

        while not current_line == '':
            lineVals = current_line.split()

            current_line_ref = lineVals[0]
            current_line_start = int(lineVals[1])

            if not (current_line_ref < data['ref'] or current_line_start < data['start']):
                file_output.append(line_to_append)
                added = True

            file_output.append(current_line)
            current_line = f.readline()

        if not added:
            file_output.append(line_to_append)

    # this could be "runtime expensive" saving here instead of just sending label data to the model itself for
    # storage
    with open(abs_path, 'w') as f:
        f.writelines(file_output)

    jh.addJob(data)

    return data


# Removes label from label file
def removeLabel(data):
    script_dir = os.path.abspath(os.path.dirname(sys.argv[0]))  # <-- absolute dir the script is in
    rel_path = cfg.dataPath + data['name'] + '_Labels.bedGraph'
    abs_path = os.path.join(script_dir, rel_path)

    output = []

    line_to_check = data['ref'] + ' ' + str(data['start']) + ' ' + str(data['end'])

    # read labels in besides one to delete
    with open(abs_path, 'r') as f:

        current_line = f.readline()

        while not current_line == '':

            if current_line.find(line_to_check) == -1:
                output.append(current_line)

            current_line = f.readline()

    # write labels after one to delete is gone
    with open(abs_path, 'w') as f:
        f.writelines(output)

    jh.addJob(data)

    return data


def updateLabel(data):
    script_dir = os.path.abspath(os.path.dirname(sys.argv[0]))  # <-- absolute dir the script is in
    rel_path = cfg.dataPath + data['name'] + '_Labels.bedGraph'
    abs_path = os.path.join(script_dir, rel_path)

    output = []

    line_to_check = data['ref'] + ' ' + str(data['start']) + ' ' + str(data['end'])

    # read labels in besides one to delete
    with open(abs_path, 'r') as f:

        current_line = f.readline()

        while not current_line == '':

            if not current_line.find(line_to_check) <= -1:
                output.append(line_to_check + ' ' + data['label'] + '\n')
            else:
                output.append(current_line)

            current_line = f.readline()

    # write labels after one to delete is gone
    with open(abs_path, 'w') as f:
        f.writelines(output)

    jh.addJob(data)

    return data


def getLabels(data):
    rel_path = cfg.dataPath + data['name'] + '_Labels.bedGraph'
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

            # If a label covers the full query
            coverQuery = ((lineStart < start) and (lineEnd > end))

            # The rest of the possible label combinations
            restQuery = ((lineStart >= start) or (lineEnd <= end))

            if lineVals[0] == refseq and (coverQuery or restQuery):
                output.append({"ref": refseq, "start": lineStart,
                               "end": lineEnd, "label": lineVals[3]})

            current_line = f.readline()

    return output


def parseHub(data):
    hub = hubParse.parse(data)
    # Add a way to configure hub here somehow instead of just loading everything
    jh.addJob(hub)
    return UCSCtoPeakLearner.convert(hub)


def getModel(data):
    print(data)

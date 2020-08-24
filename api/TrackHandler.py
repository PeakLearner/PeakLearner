import os
import sys


def jsonInput(data):
    command = data['command']
    # for some reason data['args'] is a list containing a dict
    args = data['args']
    raw_tracks = data['tracks']
    split = '%2C'
    tracks = []

    # process tracks in GET request for storage of labels
    while not (raw_tracks.find('%2C') == -1):
        find = raw_tracks.find('%2C')
        current = raw_tracks[0:find]
        tracks.append(current)
        raw_tracks = raw_tracks[(find + len(split)):]
    # if no more splits, then raw_tracks must be the last track, so add it
    tracks.append(raw_tracks)

    commandOutput = commands(command)(args, tracks)

    return commandOutput


def commands(command):
    command_list = {
        'save': addLabel,
        'remove': removeLabel,
    }

    return command_list.get(command, None)


# Adds Label to label file
def addLabel(data, tracks):
    for track in tracks:

        script_dir = os.path.abspath(os.path.dirname(sys.argv[0]))  # <-- absolute dir the script is in

        rel_path = '/data/' + track + '_Labels.bedGraph'

        file_output = []

        for feature in data:
            # A feature which labels were not messed with will have no value
            outputVal = 0
            if track in feature.keys():
                outputVal = feature[track]

            file_output.append(feature['ref'] + ' ' + str(feature['start']) +
                               ' ' + str(feature['end']) + ' ' + str(outputVal) + '\n')

        # this could be "runtime expensive" saving here instead of just sending label data to the model itself for
        # storage
        with open(script_dir + rel_path, 'w') as f:
            f.writelines(file_output)


# Removes label from label file
def removeLabel(data, tracks):

    script_dir = os.path.abspath(os.path.dirname(sys.argv[0]))  # <-- absolute dir the script is in

    # this should only really be done to one track but the current system completely deletes the highlights
    # remove this for loop and change track in rel_path to data['name'] to only delete from one track
    for track in tracks:

        rel_path = '/data/' + track + '_Labels.bedGraph'

        output = []

        line_to_check = data['ref'] + ' ' + str(data['start']) + ' ' + str(data['end'])

        # read labels in besides one to delete
        with open(script_dir + rel_path, 'r') as f:

            current_line = f.readline()

            while not current_line == '':

                if current_line.find(line_to_check) == -1:
                    output.append(current_line)

                current_line = f.readline()

        # write labels after one to delete is gone
        with open(script_dir + rel_path, 'w') as f:
            f.writelines(output)

    return data


def debug(printVal, name):
    print('\n-' + name + '--------')
    print(printVal)
    print('-End Debug----------\n')

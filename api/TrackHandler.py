

def jsonInput(data):
    command = data['command']
    args = data['args']
    raw_tracks = data['tracks']
    split = '%2C'
    tracks = []

    # process tracks in GET request for modeling the
    while not (raw_tracks.find('%2C') == -1):
        find = raw_tracks.find('%2C')
        current = raw_tracks[0:find]
        tracks.append(current)
        raw_tracks = raw_tracks[(find + len(split)):]
    tracks.append(raw_tracks)

    return commands(command)(args, tracks)


def commands(command):
    command_list = {
        'add': addLabel,
        'remove': removeLabel,
    }

    return command_list.get(command, None)


def addLabel(data, tracks):
    print(len(tracks))
    return data


def removeLabel(data, tracks):
    print("RemoveLabel")
    return data


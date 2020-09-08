import requests
import sys


def newHub(url):
    hubReq = requests.get(url, allow_redirects=True)
    file = ""
    path = ""
    if url.find('/'):
        vals = url.rsplit('/', 1)
        path = vals[0]
        file = vals[1]

    lines = hubReq.text.split('\n')

    hub = readLines(lines)
    if hub['genomesFile']:
        hub['genomesFile'] = loadGenome(hub, path)

    return hub


def loadGenome(hub, path):
    genomeUrl = path + '/' + hub['genomesFile']

    genomeReq = requests.get(genomeUrl, allow_redirects=True)

    lines = genomeReq.text.split('\n')

    output = readLines(lines)

    if output['trackDb']:
        output['trackDb'] = loadTrackDb(output, path)

    return output


def loadTrackDb(genome, path):
    trackUrl = path + '/' + genome['trackDb']

    trackReq = requests.get(trackUrl, allow_redirects=True)

    lines = trackReq.text.split('\n')

    return readLines(lines)


# Reads the lines of the current file
def readLines(lines):
    output = []
    current = {}

    outputList = False

    start = True

    added = False

    for line in lines:
        line = line.strip()
        if line == "":
            if start:
                start = False
                continue
            else:
                if not added:
                    added = True
                    output.append(current)
                    current = {}
        else:
            # If it gets to this point after adding one, then there are multiple
            if added:
                outputList = True
                added = False
            vals = line.split(" ", 1)

            current[vals[0]] = vals[1]

    if outputList:
        return output
    else:
        return output[0]


def main():
    if len(sys.argv) != 2:
        return
    hub = newHub(sys.argv[1])

if __name__ == "__main__":
    main()

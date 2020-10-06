import api.TrackHandler as th


def getModel(data):
    return []


# Calls to this function probably need to be multithreaded to not slow down the process
def updateLabelErrors(data):
    genome = th.getGenome(data)

    data['genome'] = genome

    problems = th.getProblems(data)

    for problem in problems:
        problem['name'] = data['name']

        labels = th.getLabels(problem)

        # Get models for this problem region

        # for model in models, update label errors

        # choose best model using updated errors

        # Generate new models if need be

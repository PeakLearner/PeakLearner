import LOPARTInterface
import numpy as np
import pandas as pd


def runLOPART(data, labels, penalty, n_updates=-1, inf=False, penalty_unlabeled=-1):
    if not n_updates > 0:
        n_updates = len(data)

    lenData = len(data)

    penalty_labeled = penalty
    if not penalty_unlabeled > 0:
        penalty_unlabeled = penalty

    if inf:
        penalty_labeled = 0
        penalty_unlabeled = 0

    if isinstance(data, list):
        data = np.array(data).astype(np.double)

    lopartOutput = LOPARTInterface.interface(data,
                                             lenData,
                                             (labels['start'] - 1).to_numpy(dtype=np.intc),
                                             (labels['end'] - 1).to_numpy(dtype=np.intc),
                                             labels['change'].to_numpy(dtype=np.intc),
                                             len(labels.index),
                                             penalty_labeled,
                                             penalty_unlabeled,
                                             n_updates)

    outputdf = pd.DataFrame(lopartOutput)

    outputLen = len(outputdf.index)

    addOne = outputdf['last_change'] + 1

    changeVec = addOne[0 <= addOne]

    totalChanges = len(changeVec.index)

    changes_labeled = len(labels[labels['change'] == 1].index)

    changes_unlabeled = totalChanges - changes_labeled

    complexity_labeled = calculateComplexity(changes_labeled, penalty_labeled)

    complexity_unlabeled = calculateComplexity(changes_unlabeled, penalty_unlabeled)

    complexity_total = complexity_labeled+complexity_unlabeled

    if inf:
        total_loss = outputdf['cost_optimal']
        penalized_cost = total_loss+complexity_total
    else:
        penalized_cost = outputdf['cost_optimal']
        total_loss = penalized_cost-complexity_total

    loss = {'changes_total': totalChanges,
            'changes_labeled': changes_labeled,
            'changes_unlabeled': changes_unlabeled,
            'penalty_labeled': penalty_labeled,
            'penalty_unlabeled': penalty_labeled,
            'penalized_cost': penalized_cost,
            'total_loss': total_loss}

    changes = changeVec + 0.5

    segmentsTemp = outputdf[outputdf['last_change'] != -2]

    starts = [1, ]

    changeStarts = (changeVec + 1).tolist()

    starts.extend(changeStarts)

    ends = changeVec.tolist()

    ends.extend([outputLen])

    segmentRanges = {'start': starts, 'end': ends}

    segmentsdf = pd.DataFrame(segmentRanges)

    outputSegments = segmentsdf[segmentsdf['start'] < segmentsdf['end']].copy()

    heights = segmentsTemp['mean'].tolist()

    outputSegments['height'] = heights

    return {'loss': loss, 'cost': lopartOutput, 'changes': changes, 'segments': outputSegments}


def runSlimLOPART(data, labels, penalty, n_updates=-1, penalty_unlabeled=-1):
    if not float(n_updates).is_integer():
        raise Exception
    if n_updates < 1:
        n_updates = len(data)

    lenData = len(data)

    penalty_labeled = penalty
    if not penalty_unlabeled > 0:
        penalty_unlabeled = penalty

    if isinstance(data, list):
        data = np.array(data).astype(np.double)

    lopartOutput = LOPARTInterface.interface(data,
                                             lenData,
                                             (labels['start'] - 1).to_numpy(dtype=np.intc),
                                             (labels['end'] - 1).to_numpy(dtype=np.intc),
                                             labels['change'].to_numpy(dtype=np.intc),
                                             len(labels.index),
                                             penalty_labeled,
                                             penalty_unlabeled,
                                             n_updates)

    outputdf = pd.DataFrame(lopartOutput)

    outputLen = len(outputdf.index)

    addOne = outputdf['last_change'] + 1

    changeVec = addOne[0 <= addOne]

    segmentsTemp = outputdf[outputdf['last_change'] != -2]

    starts = [1, ]

    changeStarts = (changeVec + 1).tolist()

    starts.extend(changeStarts)

    ends = changeVec.tolist()

    ends.extend([outputLen])

    segmentRanges = {'start': starts, 'end': ends}

    segmentsdf = pd.DataFrame(segmentRanges)

    outputSegments = segmentsdf[segmentsdf['start'] < segmentsdf['end']].copy()

    heights = segmentsTemp['mean'].tolist()

    outputSegments['height'] = heights

    return outputSegments


def calculateComplexity(change, penalty):
    if change == 0:
        return 0
    return change*penalty


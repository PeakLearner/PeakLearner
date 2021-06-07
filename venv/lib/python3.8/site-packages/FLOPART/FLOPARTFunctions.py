import numpy as np
import pandas as pd
import FLOPARTInterface

defaultWeight = 1


def runFLOPART(data, labels, penalty, weights=-1):
    # Create a weight vec if doesn't exist
    if weights == -1:
        weight_vec = np.full(len(data), defaultWeight, dtype=np.double)
        weights = defaultWeight
    elif isinstance(weights, np.ndarray):
        weight_vec = weights
        weights = np.average(weights)
    else:
        if weights <= 0:
            raise ValueError('Weight value must be greater than ')
        weight_vec = np.full(len(data), weights, dtype=np.double)

    lenData = len(data)
    upscale = False

    # Data must be np.ndarray type intc
    if isinstance(data, list):
        data = np.array(data).astype(np.intc)
    elif not isinstance(data, np.intc):
        upscale = True
        data = (data * weights).to_numpy(dtype=np.intc)

    flopartOutput = FLOPARTInterface.interface(data,
                                               weight_vec,
                                               lenData,
                                               (labels['start'] - 1).to_numpy(dtype=np.intc),
                                               (labels['end'] - 1).to_numpy(dtype=np.intc),
                                               (labels['change'].to_numpy(dtype=np.intc)),
                                               len(labels.index),
                                               penalty)

    # The original code had the df creation in the interface.cpp file
    # But i dont know enough about numpy to make that happen so I'm doing it here
    segments = {'start': flopartOutput['segment_starts'],
                'end': flopartOutput['segment_ends'],
                'state': flopartOutput['segment_states']}

    # If the data is scaled, also scale the average
    if upscale:
        segments['mean'] = flopartOutput['segment_means'] * weights
    else:
        segments['mean'] = flopartOutput['segment_means']

    segmentsDf = pd.DataFrame(segments)

    segmentsDf = segmentsDf[segmentsDf['start'] <= segmentsDf['end']]

    return {'cost_mat': flopartOutput['cost_mat'],
            'intervals_mat': flopartOutput['intervals_mat'],
            'segments_df': segmentsDf}


def runSlimFLOPART(data, labels, penalty, weights=-1):
    # Create a weight vec if doesn't exist
    if weights == -1:
        weight_vec = np.full(len(data), defaultWeight, dtype=np.double)
        weights = defaultWeight
    elif isinstance(weights, np.ndarray):
        weight_vec = weights
        weights = np.average(weights)
    else:
        if weights <= 0:
            raise ValueError('Weight value must be greater than ')
        weight_vec = np.full(len(data), weights, dtype=np.double)

    lenData = len(data)
    upscale = False

    # Data must be np.ndarray type intc
    if isinstance(data, list):
        data = np.array(data).astype(np.intc)
    elif not isinstance(data, np.intc):
        upscale = True
        data = (data * weights).to_numpy(dtype=np.intc)

    flopartOutput = FLOPARTInterface.interface(data,
                                               weight_vec,
                                               lenData,
                                               (labels['start'] - 1).to_numpy(dtype=np.intc),
                                               (labels['end'] - 1).to_numpy(dtype=np.intc),
                                               (labels['change'].to_numpy(dtype=np.intc)),
                                               len(labels.index),
                                               penalty)

    # The original code had the df creation in the interface.cpp file
    # But i dont know enough about numpy to make that happen so I'm doing it here
    segments = {'start': flopartOutput['segment_starts'],
                'end': flopartOutput['segment_ends'],
                'state': flopartOutput['segment_states']}

    # If the data is scaled, also scale the average
    if upscale:
        segments['mean'] = flopartOutput['segment_means'] * weights
    else:
        segments['mean'] = flopartOutput['segment_means']

    segmentsDf = pd.DataFrame(segments)

    segmentsDf = segmentsDf[segmentsDf['start'] <= segmentsDf['end']]

    return segmentsDf

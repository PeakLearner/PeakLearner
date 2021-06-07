from . import util
import PeakErrorInterface
import numpy as np
import pandas as pd


def error(peaks, regions):
    if not util.checkChrom(peaks):
        return
    if not util.checkChrom(regions):
        return

    peakGroup = peaks.groupby('chrom')
    regionGroup = regions.groupby('chrom')
    errorList = []

    for chrom in regions['chrom'].unique():
        try:
            p = peakGroup.get_group(chrom)
        except KeyError:
            p = pd.DataFrame(columns=['chrom', 'chromStart', 'chromEnd'])

        r = regionGroup.get_group(chrom)

        result = errorChrom(p, r)

        if result is not None:
            errorList.append(result)

    try:
        return pd.concat(errorList, ignore_index=True)
    except ValueError:
        return


def errorChrom(peaks, regions):
    if not util.checkPositions(peaks):
        return

    if not util.checkPositions(regions):
        return

    p = peaks.sort_values('chromStart', ignore_index=True)
    r = regions.sort_values('chromStart', ignore_index=True)

    code = r['annotation'].apply(util.toCode)
    unknown = r['annotation'][code.isnull()]

    if unknown.size > 0:
        uniques = unknown.unique()

        for unique in uniques:
            print("Annotation %s was found, invalid annotation" % unique)
            return

    output = PeakErrorInterface.interface(p['chromStart'].to_numpy(dtype=np.intc),
                                          p['chromEnd'].to_numpy(dtype=np.intc),
                                          len(p.index),
                                          r['chromStart'].to_numpy(dtype=np.intc),
                                          r['chromEnd'].to_numpy(dtype=np.intc),
                                          code.to_numpy(dtype=np.intc), len(r.index))

    outputdf = pd.DataFrame(output)

    outputdf = pd.concat(objs=[r, outputdf], axis=1)

    outputdf['fn'] = outputdf.apply(util.fnCalc, axis=1)

    outputdf['status'] = outputdf.apply(util.status, axis=1)

    return outputdf


def summarize(df):
    regions = len(df.index)
    fp = df['fp'].sum()
    possible_fp = df['possible_fp'].sum()
    fn = df['fn'].sum()
    possible_fn = df['possible_tp'].sum()
    errors = fp + fn

    outputdict = {'regions': [regions], 'fp': [fp], "possible_fp": [possible_fp],
                  'fn': [fn], 'possible_fn': [possible_fn], 'errors': [errors]}

    outputDf = pd.DataFrame(outputdict)

    return outputDf

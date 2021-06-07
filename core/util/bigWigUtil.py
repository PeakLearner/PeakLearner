import math
import subprocess


def bigWigSummary(url, chrom, start, end, bins):
    sumOut = subprocess.run(['bin/bigWigSummary',
                             url,
                             chrom,
                             str(start),
                             str(end),
                             str(bins)],
                            stdout=subprocess.PIPE).stdout.decode('utf-8')

    sumData = sumOut.split()
    floatData = []
    for i in sumData:
        if i == 'n/a':
            val = 0
        else:
            val = float(i)

        floatData.append(val)

    return floatData


def anscombeApply(val):
    return math.sqrt(val + 3/8)

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
            floatData.append(0)
        else:
            floatData.append(float(i))

    return floatData

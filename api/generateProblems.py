import os
import sys
import tempfile
import requests
import gzip
import pandas as pd


def generateProblems(genome, path):
    ucscUrl = 'http://hgdownload.soe.ucsc.edu/goldenPath/' + genome + '/database/'

    genomePath = '%sgenomes/%s/' % (path, genome)

    if not os.path.exists(genomePath):
        try:
            os.makedirs(genomePath)
        except OSError:
            return

    files = []

    for file in ['chromInfo', 'gap']:
        fileUrl = ucscUrl + file + '.txt.gz'
        output = genomePath + file + '.txt'

        files.append(downloadAndUnpackFile(fileUrl, output))

    chromInfo = pd.read_csv(files[0], sep='\t', header=None).iloc[:, 0:2]
    chromInfo.columns = ['chrom', 'bases']

    gap = pd.read_csv(files[1], sep='\t', header=None).iloc[:, 1:4]
    gap.columns = ['chrom', 'gapStart', 'gapEnd']

    join = gap.merge(chromInfo, on='chrom', how='outer')

    nan = join.isnull()['gapStart' and 'gapEnd']
    nonNan = join.notnull()['gapStart' and 'gapEnd']

    nanOutput = join[nan].groupby(['chrom']).apply(createNanProblems)

    nonNanOutput = join[nonNan].groupby(['chrom']).apply(createProblems)

    frames = [nonNanOutput, nanOutput]

    output = pd.concat(frames, sort=False)
    output['problemStart'] = output['problemStart'].astype(int)
    output['problemEnd'] = output['problemEnd'].astype(int)

    outputFile = genomePath + 'problems.bed'

    output.to_csv(outputFile, sep='\t', index=False, header=False)


def createNanProblems(args):
    data = {'chrom': args['chrom'], 'problemStart': [0], 'problemEnd': args['bases']}

    return pd.DataFrame(data)


def createProblems(group):
    chrom = group['chrom'][0]
    bases = group['bases'][0]
    problemStart = [0, ]
    gapEnd = group['gapEnd'].tolist()
    problemEnd = group['gapStart'].tolist()
    problemStart.extend(gapEnd)
    problemEnd.append(bases)

    length = len(problemStart)

    if length != len(problemEnd):
        return

    data = {'chrom': chrom, 'problemStart': problemStart, 'problemEnd': problemEnd}

    df = pd.DataFrame(data)
    return df[df['problemStart'] < df['problemEnd']]


def downloadAndUnpackFile(url, path):
    if not os.path.exists(path):
        with tempfile.NamedTemporaryFile(suffix='.txt.gz') as temp:
            # Gets FASTA file for genome
            with requests.get(url, allow_redirects=True) as r:
                temp.write(r.content)
                temp.flush()
                temp.seek(0)
            with gzip.GzipFile(fileobj=temp, mode='r') as gz:
                # uncompress the flatfile
                with open(path, 'w+b') as faFile:
                    # Save to file
                    faFile.write(gz.read())
    return path


def main():
    path = genome = ''

    if len(sys.argv) == 1:
        return

    if len(sys.argv) >= 2:
        genome = sys.argv[1]

    if len(sys.argv) >= 3:
        path = sys.argv[2]

    generateProblems(genome, path)


if __name__ == '__main__':
    main()

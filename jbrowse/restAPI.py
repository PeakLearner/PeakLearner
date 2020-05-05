from flask import Flask, request, Response
from flask_cors import CORS
import json as simplejson
import requests
import bbi

#api set up
app = Flask(__name__)
CORS(app)

@app.route('/refSeqs.json')
def ref_seqs():
    featList = []
    sizeDict = bbi.chromsizes('data/joint_peaks.bigWig')
    index = 1
    for entry in sizeDict:
        name = 'chr' + index
        if index - 1 <= 0:
            start = 0
        else:
            start = sizeDict['chr' + (index - 1)]
        end = sizeDict[name]
        newDict = {"name": name, "start": start, "end": end}
        featList.append(simplejson.dumps(newDict))
        index = index + 1
    return featList

@app.route('/stats/global')
def get_stats():
    featList = { 'featureDensity' : 0.2 }
    return simplejson.dumps(featList)

@app.route('/features/<refseq>')
def get_model(refseq):
    start = int(request.args.get('start'))
    end = int(request.args.get('end'))
    print(request.args.get('flag'))
    arr = bbi.fetch('data/joint_peaks.bigWig', 'chr1', start, end)
    featList = []
    index = 0

    while index < len(arr):
        if arr[index] != 0:
            start = index
            value = arr[index]
            while index < len(arr) and arr[index] == value:
                index = index + 1
            end = index
            newList = {"start": start, "end": end, "score": value}
            featList.append(newList)
        index = index + 1
        
    return simplejson.dumps({ 'features' : featList })
    
@app.after_request
def apply_caching(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Origin, X-Requested-With, Content-Type, Accept"
    return response

app.run()

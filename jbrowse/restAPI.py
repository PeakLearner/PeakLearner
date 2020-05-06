from flask import Flask, request, Response
from flask_cors import CORS
import json as simplejson
import requests
import urllib
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
    json = {'features': []}
    for entry in bbi.fetch_intervals('data/joint_peaks.bigWig', 'chr1', start, end):
        inter = { "start": entry[1], "end": entry[2], "score": entry[3] }
        json['features'].append(inter)
    return simplejson.dumps(json)
    
@app.after_request
def apply_caching(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Origin, X-Requested-With, Content-Type, Accept"
    return response

app.run()

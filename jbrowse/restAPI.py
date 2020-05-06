# These are for handaling api calls
from flask import Flask, request, Response
from flask_cors import CORS

# this is used to transform python dicts to json
import json as simplejson

# this is used to parse the bigwigs
import bbi

#api set up, initalize flask
app = Flask(__name__)
CORS(app)

'''
    ================== overview of code  ==================
    
    This is the code for the REST api that enables the model to
        be updated upon getting a new label. This api needs to 
        be a REST api becuase that is how jbrowse requiers it to
        use the REST store class. If you want to know more about
        store classes you can find more in the jbrowse readme 
        or in the overview for the interactivePeakAnnottor
        
    there are 4 functions in this api and most of them are purly
        becuase jbrowse needs certain functions to exist for it
        to run properly. The only one that is very important is
        get_model(). this is responsible for handing off the
        approprite information to the browser.
        
    For more information about the jbrowse rest api requierments
        you can go to https://jbrowse.org/docs/data_formats.html
        
    This api was based of of one by hexylena on github, you can
        that repository here https://github.com/hexylena/JBrowse-REST-API-Example
    
    ================== end of overview  ===================
'''

# used for getting the chrom sizes of a refrence sequence
# currently is not used 
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


# used to get stats of the sequence
# curently is not used
@app.route('/stats/global')
def get_stats():
    featList = { 'featureDensity' : 0.2 }
    return simplejson.dumps(featList)

# used to get a list of all non zero features in the range requested
# the features are the non zero sections of the model
# NOTE: currently only works with bigWig, and wig tracks
@app.route('/features/<refseq>')
def get_model(refseq):
    start = int(request.args.get('start'))
    end = int(request.args.get('end')) - 1
    json = {'features': []}

    file_path = '/home/jacob/Documents/School/Capstone/PeakLearner-1.1/jbrowse/data/joint_peaks.bigWig'
    
    for entry in bbi.fetch_intervals(file_path, 'chr1', start, end):
        inter = { "start": entry[1], "end": entry[2], "score": entry[3]}
        json['features'].append(inter)
    
    return simplejson.dumps(json)

# this is to help allow cors communication
# currently is probably redundant with the flask cors we imported
# curently is not used
@app.after_request
def apply_caching(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Origin, X-Requested-With, Content-Type, Accept"
    return response

# starts the api when the code is run
app.run()

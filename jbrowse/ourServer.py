#!/usr/bin/python


#These are needed to handle range requests
import os
import re
import BaseHTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler

#api handaling
from flask import Flask
from flask_cors import CORS

#These are needed to handle the database
#import db

#these are needed to handle our post requests
import json as simplejson
from io import BytesIO

#these are needed to run R scripts
import subprocess

#for api requests to read bigwig
import bbi

PORT_NUMBER = 8081

#https://github.com/danvk/RangeHTTPServer
#see link above for original code which we copied here to properly extend
def copy_byte_range(infile, outfile, start=None, stop=None, bufsize=16*1024):
    '''Like shutil.copyfileobj, but only copy a range of the streams.
    Both start and stop are inclusive.
    '''
    if start is not None: infile.seek(start)
    while 1:
        to_read = min(bufsize, stop + 1 - infile.tell() if stop else bufsize)
        buf = infile.read(to_read)
        if not buf:
            break
        outfile.write(buf)


BYTE_RANGE_RE = re.compile(r'bytes=(\d+)-(\d+)?$')
def parse_byte_range(byte_range):
    '''Returns the two numbers in 'bytes=123-456' or throws ValueError.
    The last number or both numbers may be None.
    '''
    if byte_range.strip() == '':
        return None, None

    m = BYTE_RANGE_RE.match(byte_range)
    if not m:
        raise ValueError('Invalid byte range %s' % byte_range)

    first, last = [x and int(x) for x in m.groups()]
    if last and last < first:
        raise ValueError('Invalid byte range %s' % byte_range)
    return first, last



# apiSetup
app = Flask(__name__)
CORS(app)

@app.route("/", methods=['GET', 'OPTIONS'])
def restGet():
    print('got to restGet()')
    arr = bbi.fetch('data/joint_peaks.bigWig', 'chr1', 0, 29000)
    featList = []
    index = 0

    while index < len(arr):
        if arr[index] != 0:
            start = index
            value = arr[index]
            while index < len(arr) and arr[index] == value:
                index = index + 1
            end = index
            newList = {'start': start, 'end': end, 'value': value}
            featList.append(newList)
        index = index + 1
        
    return simplejson.dumps(featList)


class RangeRequestHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        if 'Range' not in self.headers:
            self.range = None
            return SimpleHTTPRequestHandler.send_head(self)
        try:
            self.range = parse_byte_range(self.headers['Range'])
        except ValueError as e:
            self.send_error(400, 'Invalid byte range')
            return None
        first, last = self.range

        # Mirroring SimpleHTTPServer.py here
        path = self.translate_path(self.path)
        f = None
        ctype = self.guess_type(path)
        try:
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, 'File not found')
            return None

        fs = os.fstat(f.fileno())
        file_len = fs[6]
        if first >= file_len:
            self.send_error(416, 'Requested Range Not Satisfiable')
            return None

        self.send_response(206)
        self.send_header('Content-type', ctype)
        self.send_header('Accept-Ranges', 'bytes')

        if last is None or last >= file_len:
            last = file_len - 1
        response_length = last - first + 1

        self.send_header('Content-Range',
                         'bytes %s-%s/%s' % (first, last, file_len))
        self.send_header('Content-Length', str(response_length))
        self.send_header('Last-Modified', self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f

    def copyfile(self, source, outputfile):
        if not self.range:
            return SimpleHTTPRequestHandler.copyfile(self, source, outputfile)

        # SimpleHTTPRequestHandler uses shutil.copyfileobj, which doesn't let
        # you stop the copying before the end of the file.
        start, stop = self.range  # set in send_head()
        copy_byte_range(source, outputfile, start, stop)

    def do_POST(self):
        print('Got a post')
        # first parse out the infomation we got from the post 
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        self.send_response(200)
        self.end_headers()
        jsondata = simplejson.loads(body)

        #print a few tests to make sure it is what is expected
        print(jsondata)
#        allLabelsArray = jsondata["test"]
#        print(allLabelsArray)

        #put the labels we got into our database
#        testDB = db.testDB
#        for label in allLabelsArray:
#            print(label)
#            print("label above")
#            key_name = 'start' + str(label)
#            key = 'b' + key_name
#            testDB.put(key,str(label))
#        
#        print("database test")
#        print(testDB.get(b'starta'))
        
        #this model is just a placeholder for now
        #get an optimal Model and turn it into a JSON object here
        model = simplejson.dumps({'model': 'myModel.bigWig', 'errors':'1'})


        #This next block is our simulation of the cluster and using Dr. Hockings R code
        ############################################

        # Define command and arguments
        #command = 'Rscript'
        #path2script = '../PeakSegDisk-master/R/PeakSegFPOP_dir.R'

        # the function we want to run has 2 arguments
        #a path to the coverage data we are observing
        #penatly > 0
        #args = ['path/to/coverageData', '1']

        # Build subprocess command
        #cmd = [command, path2script] + args

        # check_output will run the command and store to result
        #newModel = subprocess.check_output(cmd, universal_newlines=True)

        #print('The new model we got from R:', newModel)
        ############################################
        #For now, in this section we will always send back a specific model which we will write to here
        script_dir = os.path.dirname(__file__) #<-- absolute dir the script is in
        rel_path = "data/tracks.conf"
        abs_file_path = os.path.join(script_dir, rel_path)

        with open(abs_file_path, 'r') as file:
            # read a list of lines into data
            data = file.readlines()


        # now change the line, note that you have to add a newline
        fakemodel1 = 'urlTemplates+=json:{"url":"joint_peaks.bigWig", "name": "joint peaks", "color": "red", "lineWidth":"3"}\n'
        fakemodel2 ='urlTemplates+=json:{"url":"coverage.bigWig", "name": "Coverage", "color": "blue"}\n'
        print(data[7])
        print(data[7] == fakemodel2)
        if data[7] == fakemodel2:
            data[7] = fakemodel1 
        else:
            data[7] = fakemodel2 

        # and write everything back
        with open(abs_file_path, 'w') as file:
            file.writelines( data )        
        #model = do something with the parser and the trackhub       
        ############################################

        #write a response containing the optimal model and send it back to the browser
        response = BytesIO()
        response.write(model)
        self.wfile.write(response.getvalue())

try:
    #Create a web server and define the handler to manage the
    #incoming requests
    server = BaseHTTPServer.HTTPServer(('', PORT_NUMBER), RangeRequestHandler)
    print ('Started httpserver on port ', PORT_NUMBER)
    #Wait forever for incoming http requests
    server.serve_forever()

except KeyboardInterrupt:
    #This is the way to close the server, by hitting control + c
    print ('^C received, shutting down the web server')
    server.socket.close()

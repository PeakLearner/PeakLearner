import http.server as server
import os
import re
import json
import socketserver
import threading
from api import TrackHandler
from signal import signal, SIGINT
import sys

# https://github.com/danvk/RangeHTTPServer
# see link above for original code which we copied here to properly extend


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


class RangeRequestHandler(server.SimpleHTTPRequestHandler):
    def send_head(self):
        if 'Range' not in self.headers:
            self.range = None
            return server.SimpleHTTPRequestHandler.send_head(self)
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
            return server.SimpleHTTPRequestHandler.copyfile(self, source, outputfile)

        # SimpleHTTPRequestHandler uses shutil.copyfileobj, which doesn't let
        # you stop the copying before the end of the file.
        start, stop = self.range  # set in send_head()
        copy_byte_range(source, outputfile, start, stop)

    def do_POST(self):
        # first parse out the information we got from the post
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        # need to decode as the body is a byte string
        decode = body.decode()
        json_val = json.loads(decode)

        # Sends data to TrackHandler
        output = TrackHandler.jsonInput(json_val)

        # TODO: Add better error handling
        if output:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(output).encode('utf8'))
        else:
            self.send_response(204)
            self.end_headers()


class ThreadingHTTPServerWithDirectory(server.ThreadingHTTPServer):
    def __init__(self, *args, directory='', **kwargs):
        if directory == '':
            directory = os.getcwd()
        else:
            directory = os.path.join(os.getcwd(), directory)
        self.directory = directory
        super().__init__(*args, **kwargs)

    def finish_request(self, request, client_address):
        self.RequestHandlerClass(request, client_address, self, directory=self.directory)


http_server = None


def httpserver(port, path):
    global http_server
    handler = RangeRequestHandler
    http_server = ThreadingHTTPServerWithDirectory(('', port), handler, directory=path)
    print("Started HTTP server on port", port)
    http_server.serve_forever()


def shutdownServer():
    print('Shutting down PeakLearner')
    if http_server is not None:
        http_server.shutdown()


def interrupt_handle(signal, frame):
    print('\nHandling interrupt')
    shutdownServer()


signal(SIGINT, interrupt_handle)

# PeakLearner-1.1
The initial version of the technical demo


----------Server-----------

To run the server, install all necessary dependencies and run the following command:
	./ourServer.py
from within the jbrowse folder. Starting inside the folder make it easier on jbrowse when it is trying to get all of
the data it needs to initialize.

Some of the important packages that must be installed first include:
	berkeley-db
	bsddb3
	http.server


The server handles get requests in the same manner as the python SimpleHTTPServer.
The server uses code copied from https://github.com/danvk/RangeHTTPServer to handle range requests.
The code was copied instead of just called directly because it had to be modified in order to work.
coddrectly with JBrowse to send back parts of the data files instead of the entire file. 

The server also handles post requests that send in labels and return back to the browser a model.

All of this code can be found in the jbrowse/ourServer.py file.

----------Database----------
The database is a nonrelational database using A combination of BerkeleyDB and code from Dr. Toby Hocking 
at Northern Arizona University. The code modified to create our database can be found at
https://github.com/tdhock/SegAnnDB

It is important to note that the db files can not be opened and read like a traditional database. 
To access the files use commands like
	db.get() 	or
	db.put()	

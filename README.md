# PeakLearner-1.1
The initial version of the technical demo


## ToDo
    1. True Positive Vs False Positive matrix
                This is used to calculate the best model, and if one isnt found then send to the cluster to generate a new one. This should be done inside of the "do_Post()" methond inside ourServer.py. This is the function that handles the incoming labels from the browser. 
    2. 

## Server

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

## Database
The database is a nonrelational database using A combination of BerkeleyDB and code from Dr. Toby Hocking 
at Northern Arizona University. The code modified to create our database can be found at
https://github.com/tdhock/SegAnnDB

It is important to note that the db files can not be opened and read like a traditional database. 
To access the files use commands like
	db.get() 	or
	db.put()	
	
	
## Jbrowse

index:
1. Setup
2. Terminology/ About jbrowse
3. Architecture (plugins, functions etc)
4. Refrences

### Setup

First clone the repository found at "https://github.com/yf6666/PeakLearner-1.1". cd in to "PeakLearner-1.1/jbrowse". To inizalize jbrowse you will need to run a script and create a directory inside of jbrowse. first run setup.sh, to run this type in to the terminal "./setup.sh". This may take several minutes, as this makes sure that all nessassary dependencies of jbrowse. This will include downloading perl and nodejs dependencies, as well as some test data called "volvox". Before running the next script create a directory called "data" inside the main jbrowse directory, ie "../PeakLearner-1.1/jbrowse/data".

1. clone repository from "https://github.com/yf6666/PeakLearner-1.1"
2. git checkout <new branch if needed>
3. change directory to "../PeakLearner-1.1/jbrowse"
4. run "./setup.sh"
5. create a directory inside of jbrowse named data, ie "../PeakLearner-1.1/jbrowse/data"

### Terminology/ About jbrowse

To have jbrowse show some information a tracks.conf or trackList.json file inside of "../PeakLearner-1.1/jbrowse/data" needs to be created. When first designing this the Gnomes team primarily used the tracks.conf method, so some of the resources and how to use them will be primarly focused on that. Below is an example of a tracks.conf file followed by a breakdown of some of its terms

[GENERAL]
refSeqs=volvox.fa.fai

[tracks.refseq]
urlTemplate=volvox.fa
storeClass=JBrowse/Store/SeqFeature/IndexedFasta
type=Sequence
key=volvox refrence

[ tracks.my-bigwig-track ]
storeClass = JBrowse/Store/SeqFeature/BigWig
urlTemplate = myfile.bw
type = JBrowse/View/Track/Wiggle/XYPlot
key = Coverage plot of NGS alignments from XYZ

General: is a heading to denote where information that will apply to all the tracks in the file. The only requierd assignment here is "refSeqs" as this is used by jbrowse to know where in the file the user is curently looking accross all of the tracks in the file.

tracks.'name': Each track needs to have a tracks.'name' to denote it. The 'name' needs to be unique and will be the name that is passed to the server later on when adding and removing labels. Below this will be all of the setup for the track in question.

urlTemplate: This is the relative path or url to the file.

storeClass: This dictates how the file is stored by jbrowse. there are more types of store classes then what is shown above, to find some of the other ones for basic file types you can go to "jbrowse/src/Jbrowse/store/SeqFeature". The other important kinds of storeClass is those from plugins. To find these go in to "jbrowse/plugins/""PLUGIN NAME""/js/Store/SeqFeature". 

type: This is a designation of what kind of track the file is. It determines how the file behaves to user input. Some basic types are "Sequence" and "Alignments2". For some more specific ones you can go to "JBrowse/View/Track/""TRACK TYPE""/". Just as with storeClass type can also be inside of a plugin at "jbrowse/plugins/""PLUGIN NAME""/js/View/Track"

key: is the name that will actually be displayed in the browser

### Architecture (plugins, functions etc)

Before getting in to anything specific first it is important to understand the plugins that build up to make PeakLearner. There are three plugins: MultiBigWig, WiggleHighlighter, and InteractivePeakAnotator. Each of these can be found inside of "jbrowse/plugins" along with some other plugins that ship with basic jbrowse. MultiBigWig is the basis of PeakLearner, it allows for multiple bigwig files to be shown on the same track. WiggleHighlighter extends this and set up some ability to show highlights on top of the bigwigs. Finally InteractivePeakAnotator wich handles most of what is important to adding removing labels, and will be primarily the focus for the rest of this read me. 

To understand how PeakLearner, it is important to know the interacting parts. There are 5 parts that this readme will go over: main.js, MultiXYPlot.js, tracks.conf, index.html, and restAPI.py.

main.js
All plugins are requierd to have a main.js directly inside of their js foulder. This is where anything that needs to be setup when the track is made is inizalized. Inside of the main.py for PeakAnnotator is the setup for starting and sending labels. This is done through setting up a listiner on the jbrowse event "globalHighlightChanged". This grabs 2 things, the range of the new highlight that was just applied, and an empty element when the user exits the highlight tool. If the listiner recieves a range then it saves the highlight to localStorage so it can start showing a label in that area. This also sets a highlight flag for later use to determine if the user is editing or removing labels. If the listiner recieves an empty element then it parses the information stored in localStorage to get the start, end and label type and sends it to the server for processing. This has the effect that a user can create a label, edit it, and then save the label.

MultiXYPlot.js
This is the type for PeakLearner tracks. This file handles changing what kind of label a specific label is, ie "unknown", "Peak", "No Peak", "Peak Start", and "Peak End". It does this by creating three functions onHighlightClick, highlightColor, and indicatorColor. The last 2 just determine the color of a label based off of its type. onHighlightClick is in charge changeing the type of label or removing it depending on the highlight flag set by main.js. If the highlight flag is true then highlights are still being edited, so when onHighlightClick detects that a highlight was clicked then it finds that label in localStorage and increases the label type by one. For this reason the label type is stored as a number 0 is "uknown", 1 is "Peak" and so fourth. It also uses mod to not ever have a label type beyond the 5 allowed kinds. If the highlight flag is false, then onHighlightClick removes the label from localStorage and sends a post to the server to let it know what label was removed.

tracks.conf
Below is an example of how to set up a tracks.conf for a PeakLearner track. 

[tracks.interactive]
key=Interactive MultiXYPlot
type=InteractivePeakAnnotator/View/Track/MultiXYPlot
urlTemplates+=json:{"url":"coverage.bigWig", "name": "volvox_positive", "color": "#235"}
urlTemplates+=json:{"storeClass": "JBrowse/Store/SeqFeature/REST", "baseUrl":"http://127.0.0.1:5000", "name": "joint_peaks", "color": "red", "lineWidth": 5, "noCache": true}
storeClass=MultiBigWig/Store/SeqFeature/MultiBigWig
storeConf=json:{"storeClass": "InteractivePeakAnnotator/Store/SeqFeature/Features"}

This is much like a normal bigwig track but with a few exceptions. First is the urlTemplates, instead of a path or url you will add new json objects with some information on the bigwig. It is important to notice it is '+=' for urlTemplates not an '='. These json objects can be thought of as mini track configurations for the bigwig inside. For the second urlTemplate you even define a diffrent storeClass, the new one being for a REST file. This along with noCache being true, is what makes it so that the model is updated immediatly. The REST store class makes it so that jbrowse asks a outside api in order to get the sequence information and the noCache means that jbrowse wont store the information locally, making it so that once the model updates on the server side it will update on the user side. 

index.html
There is not much here but this is where the function sendPost() is defined. sendPost() is used in both main.js and MultiXYPlot.js.

restAPI.py
This is an api that meets the requeirments of jbrowse in order to use the rest store class. Inside there are several functions but the only one that is really needed is the get_model() function. This is the funcion that parses the bigwig on the server side and sends a json inside a json with the form of {'features': [{ "start": XXX, "end": YYY, "score": ZZZ}, ... ]}. You can have any amount of { "start": XXX, "end": YYY, "score": ZZZ} inside of the list.

## Refrences

Jbrowse Documentation               https://jbrowse.org/docs/installation.html
gmod wiki                           http://gmod.org/wiki/JBrowse
Jbrowse git                         https://github.com/GMOD/jbrowse/
PeakLearner git                     https://github.com/yf6666/PeakLearner-1.1
MultiBigWig git                     https://github.com/elsiklab/multibigwig
WiggleHighlighter git               https://github.com/cmdcolin/wigglehighlighter/issues/1
InteractivePeakAnnotator git        https://github.com/cmdcolin/interactivepeakannotator

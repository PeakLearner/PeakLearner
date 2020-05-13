# PeakLearner-1.1
The initial version of the technical demo


## ToDo
    1. True Positive Vs False Positive matrix
                This is used to calculate the best model, and if one isnt found then send to the cluster to generate a new one. This should be done inside of the "send_Post()" method inside ourServer.py. This is the function that handles the incoming labels from the browser. 
    2. Connect to the Cluster. This will also be done inside of the send_post function inside of the ourServer.py file. There was a code stub immediately after adding data to the database where a presumptive cluster call could be made.

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
correctly with JBrowse to send back parts of the data files instead of the entire file.
This rangeRequestHandler is implemented in ourServer.py

The server also handles post requests that send in labels and return back to the browser a model.

All of this code can be found in the jbrowse/ourServer.py file.

A video of the server setup can be found here: https://drive.google.com/file/d/1q0bEv5baiAuYGZEeP7WNdubQVjJ0ogZR/view?usp=sharing

A complete virtual box image of the machine the video was recorded on can be found here:
To use the image, unzip the file. Then download virtualbox. Lastly click add and point the system at the folder that was unzipped to set up the machine. 

## Database
The database is a nonrelational database using A combination of BerkeleyDB and code from Dr. Toby Hocking 
at Northern Arizona University. The code modified to create our database can be found at
https://github.com/tdhock/SegAnnDB

It is important to note that the db files can not be opened and read like a traditional database. 
To access the files use commands like
	db.get() 	or
	db.put()	
	
	Currently there is a database to store the labels. Each label is stored in an array of labels as a value in a json object. These are stored on a per track level as to not confuse the labels across tracks. Each track has a single array of labels for it. There was also a plan of storing all model filenames and error counts as a second database to save time on having to communicate with the cluster. 
	
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
    urlTemplates+=json:{"storeClass": "JBrowse/Store/SeqFeature/REST", "baseUrl":"http://127.0.0.1:5000", "name": "joint_peaks", "color": "red", "lineWidth": 5, "noCache": true, "query": {"name": "joint_peaks.bigWig"}}
    storeClass=MultiBigWig/Store/SeqFeature/MultiBigWig
    storeConf=json:{"storeClass": "InteractivePeakAnnotator/Store/SeqFeature/Features"}

This is much like a normal bigwig track but with a few exceptions. First is the urlTemplates, instead of a path or url you will add new json objects with some information on the bigwig. It is important to notice it is '+=' for urlTemplates not an '='. These json objects can be thought of as mini track configurations for the bigwig inside. For the second urlTemplate you even define a diffrent storeClass, the new one being for a REST file. This along with noCache being true, is what makes it so that the model is updated immediatly. The REST store class makes it so that jbrowse asks a outside api in order to get the sequence information and the noCache means that jbrowse wont store the information locally, making it so that once the model updates on the server side it will update on the user side. 

index.html
There is not much here but this is where the function sendPost() is defined. sendPost() is used in both main.js and MultiXYPlot.js.

restAPI.py
This is an api that meets the requeirments of jbrowse in order to use the rest store class. Inside there are several functions but the only one that is really needed is the get_model() function. This is the funcion that parses the bigwig on the server side and sends a json inside a json with the form of {'features': [{ "start": XXX, "end": YYY, "score": ZZZ}, ... ]}. You can have any amount of { "start": XXX, "end": YYY, "score": ZZZ} inside of the list.

## Feature walkThrough

This section will be a walkthrough of a user interacting with PeakLearner, and what happens in the code. This will go through some of the features of peakLearner. This is accurat as of may 7th 2020 or just around the commit 39ffb94f66d732cbddce0105bf202ca30a24fc37.

First Load:
This is assuming that you have set up jbrowse as defined above. When the page is first loaded the server will start loading the pages and running the code to start and run jbrowse. The code that handles this can be found in the "send_Head()" method inside of "ourServer.py". 
Once jbrowse is served it will began to inizalize its dependencies. First will be the plugins defined in jbrowse_conf.json. Each plugin will print to the console when they are inizalized. The three plugins that should print is "MultiBigWig", "WiggleHighligher", and "InteractivePeakAnnotator". If another plugin is added you will need to do three things. First place the plugin in to the plugins folder, next you will need to add the plugins name in to jbrowse_conf.json and finally type "npm run build" in to the terminal. 
Next jbrowse will load in the tracks in tracks.conf. Each track will be saved under the unique name you write in [tracks.<name>]. Each track will be inizalized seperatly meaning if one fails to find its data, or is set up incorectly it should not effect the other tracks from loading. If a track fails to load instead jbrowse will show an error where the track should be and print to the console more about the error. If anything goes wrong jbrowse will instead print to an error screen at the bottom of this screen will be a description of what went wrong. If you get a screen that says "Jbrowse is on the web..." it should confirm you have run ./setup.sh but the issue is that jbrowse could not find a data foulder or the foulder you directed it towords for data. If everything has been completed without error it will bring you to a screen with all of the tracks. 

Navigation:
Moving through the tracks will cause jbrowse to call a reDraw() of each track being moved which sends more get requests to be sent to the server, this is again handled by the "send_Head()" method. reDraw() is function that is built in to jbrowse and has not been modified. NOTE if any of your tacks are InteractivePeakAnnotator track moving through the track will also send get requests to the "get_model()" method inside of the restAPI.py file. This method will grab the name of the approprite model file from the query and then parse through the range given by jbrowse. It then grabs all of the non zero sections of the model that overlap with the given range. After that it rearanges the the information in to that of what jbrowse expects, a json object with one key called label that maps to a list of jsons with a start end and score.

NOTE Below this point everything only applies to the InteractivePeakAnnotator tracks

Adding a Label:
Adding a new label is started by clicking the builtin highlight button. This will allow a user to click and drag a highlight on to a track. Any interactivePeakAnnotator track will have been inizalized with a listner for any highlights. This listner will grab this highlight and create a new "feature" and store it in localStorage. This will also rais a flag that makes it so that the label can be edited untill the user exits the highlight tool. Once the user exits the highlight tool the lisner will grab all of the labels from localStorage and compile it in to a json to send to the server. 
NOTE all of the code for adding a label is in the "main.js" file of the InteractivePeakAnnotator plugin.

Editing a Label: 
A user can edit a label after they have added the highlight but before they have left the highlight tool. To change the type of the label click inside of it. It will cycle through "unknown", "Peak", "No Peak", "Peak Start", and "Peak End". This is done inside of the "MultiXYPlot.js" file inside of InteractivePeakAnnotator. 
OnHighlightClick() will grab the labels from local storage and has an array of the types of labels listed above. When a label is clicked the method goes through these labels to find the one that has been clicked. It then increments the number stored inisde of this json, that is keyed to the tracks name. If the label is new and has not been clicked before, this method will add a key to the json of the label under the tracks name. With muiltiple Tracks being adding labels too this will resualt in the json having a key to each track corrisponding to a number representing the type. An example of this is below:
    {"start": XXX, "end": YYY, "ref": ZZZ, "track1": i, "track2": j, "track3": k}
The color is determend by highlightColot() and indecatorColor() which are both in "MultiXYPlot.js". Both of these grab the track type from the label json and use that as an index in a color list.

Removing a Label:
Removing a label can be done by clicking on the label at any time after the highlight tool has been closed. This will activate the "onHighlightClick()" method in the "MultiXYPlot.js" file of the InteractivePeakAnnotator plugin. This method will loop through the labels in localStorage and remove the one that was clicked on.

## rest API

The rest API is a system that jbrowse has inplace for retrieving data across the internet. PeakLearner is designed to have the model of an InteractivePeakAnnotator retrieved using the rest API implemented in "restAPI.py". The only function that is used right now is the "get_model()" function. The rest are supposed to be there however in the setup described above on how to set up an IPA track it dosent need any of the other ones. 

tracks.conf
When creating the track information inside of tracks.conf it is important to configure the model urltemplate with the correct information. Below is the urlTemplate for an example model:
'''
urlTemplates+=json:{"storeClass": "JBrowse/Store/SeqFeature/REST", "baseUrl":"http://127.0.0.1:5000", "name": "joint_peaks", "color": "red", "lineWidth": 5, "noCache": true, "query": {"name": "joint_peaks.bigWig"}}
'''
The very first thiing is assigning this specific bigwig to the REST store class, this will make jbrowse call the api at the url in "baseURL". The name, color, and lineWidth are all style choices for a line and can be set to most anything. NOTE the only exception is the name, it has to be unique in the file. To have the model update in real time the "noCache" needs to be set to true, otherwise jbrowse would start to store pieces of the model locally and while this would be quicker it would not ask for the new information. With "noCache" set to true, everytime a redraw is called on the track, jbrowse will request the information again from the api. The final element is the "query" key. The "query" key an have a json object of arbatrary length, that is sent with every call to the api. Currently this is used to pass the name of the model to the api.

restAPI.py
"get_model()" is the funciton that handles an incomming call to the path "feature/<refSeq>". First the method parses the query information to get the start and end of the information being asked for. Followed by finding the refseq which is misleading as that is the chromasom the information is comming from. And finally the queary also has the information about what the name of the model should be. Using the name of the model and the files position it creates the appropriate path name for the model in question. It then uses a python library called "bbi" to fetch all of the non zero ranges of bases that overlap with the range requested. This gives the correct information but it is not in the correct format of what jbrowse expects. The loop takes the information from the information that "bbi" gives and converts it in to the right format. 
	
## Travis-CI
The .travis.yml file in the top-level directory is configuration file for running integration tests on Travis-CI. A block in the yml file corresponds to each phase of the build:
```
language: python
version:
  - "2.7"
```
Since some of our dependencies rely on Python 2.7, that is the version we use for testing.
```
before_install:
  ...
```
In this phase, we install slurm-llnl (the scheduling software Monsoon uses) and any other dependencies.
```
script:
  python tests/cluster_tests/clusterTest.py
```
Testing scripts go in this block.
```
branches:
  - test-branch
notifications:
  ...
```
When a new commit is pushed to a specified branch (in this case test-branch), a Travis build is triggered. Specify email or slack notifications in the next block.

# References

Jbrowse Documentation               https://jbrowse.org/docs/installation.html

gmod wiki                           http://gmod.org/wiki/JBrowse

Jbrowse git                         https://github.com/GMOD/jbrowse/

PeakLearner git                     https://github.com/yf6666/PeakLearner-1.1

MultiBigWig git                     https://github.com/elsiklab/multibigwig

WiggleHighlighter git               https://github.com/cmdcolin/wigglehighlighter/issues/1

InteractivePeakAnnotator git        https://github.com/cmdcolin/interactivepeakannotator

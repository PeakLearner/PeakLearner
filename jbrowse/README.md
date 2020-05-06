# Installing JBrowse

To install jbrowse, visit http://jbrowse.org/blog and download the latest JBrowse zip file. See instructions at http://jbrowse.org/docs/installation.html for a tutorial on setting up a sample instance.


# Install JBrowse from GitHub (for developers)

To install from GitHub, you can simply clone the repo and run the setup.sh script

    git clone https://github.com/GMOD/jbrowse
    cd jbrowse
    ./setup.sh

## Note for users in China

In order to make downloads faster you can set a mirror for the npm registry

    npm config set registry http://r.cnpmjs.org
    npm config set puppeteer_download_host=http://cnpmjs.org/mirrors
    export ELECTRON_MIRROR="http://cnpmjs.org/mirrors/electron/"


## Notes on setting up a JBrowse server

* If you don't have a webserver such as apache or nginx, you can run `npm run start` and open http://localhost:8082/index.html?data=sample_data/json/volvox to see the code running from a small express.js server.

* You can alternatively just move the jbrowse folder into a nginx or apache root directory e.g. /var/www/html and then navigate to http://localhost/jbrowse



*Note: you should avoid using sudo tasks like ./setup.sh and instead use chown/chmod on folders to your own user as necessary.*

*Also note: After editing a file, you must re-run the webpack build with `npm run build` or you can keep webpack running in "watch" mode by running  `npm run watch`.*

*Also also note: by default `git clone` will clone the master branch which contains the latest stable release. The latest development branch is called dev. Run `git checkout dev` after clone to retrieve this*

# Installing as an npm module

To install jbrowse from NPM directly, you can run.

    npm install @gmod/jbrowse

To setup a simple instance, you can use

    node_modules/.bin/jb_setup.js
    node_modules/.bin/jb_run.js

Then visit http://localhost:3000/?data=sample_data/json/volvox

# Contributing

Looking for places to contribute to the codebase?
[Check out the "help wanted" label](https://github.com/GMOD/jbrowse/labels/help%20wanted).

# Running the developer test suites

The Travis-CI suite runs Perl, JavaScript, and Selenium automated tests. To run locally, you can use

    prove -Isrc/perl5 -lr tests
    node tests/js_tests/run-puppeteer.js http://localhost/jbrowse/tests/js_tests/index.html
    pip install selenium nose
    MOZ_HEADLESS=1 SELENIUM_BROWSER=firefox JBROWSE_URL='http://localhost/jbrowse/index.html' nosetests

Supported browsers for SELENIUM_BROWSER are 'firefox', 'chrome', 'phantom', and 'travis_saucelabs'.  The Sauce Labs + Travis
one will only work in a properly configured Travis CI build environment.

# Manual testing

<img style="display: block; margin: 1em auto" src="img/browserstack-logo-600x315.png" width="200" alt="Browserstack"/>

JBrowse has a free open source account on [Browserstack](http://browserstack.com/) for manual testing.  Contact @rbuels for access.

# Generating Packaged Builds

You can also optionally run build steps to create the minimized codebase. Extra perl dependencies Text::Markdown and DateTime are required to run the build step.

    make -f build/Makefile

To build the Electron app (JBrowse desktop app), run the following

    npm install -g electron-packager
    make -f build/Makefile release-electron-all

To run the Electron app in debug mode run the following

    npm install -g electron
    electron browser/main.js


# Making a JBrowse release

NOTE: Beginning in 1.12.4,

1. Run `build/release.sh $newReleaseVersion $nextReleaseVersion-alpha.0 notes.txt`, where notes.txt is any additional information to add to a blogpost. Then check its work, and then run the `git push` command it suggests to you. This makes a tag in the repository for the release, named, e.g. `1.6.3-release`.  This should cause Travis CI
to create a release on GitHub under https://github.com/GMOD/jbrowse/releases

1. Test that the page loads in IE11 on BrowserStack

1. Add release notes to the new GitHub release that Travis created. Can just paste these from release-notes.md, which is in Markdown format.

1. Write a twitter post for usejbrowse and JBrowseGossip with the announcement link to the blogpost

1. Write an email announcing the release, sending to gmod-ajax. If it is a major release, add gmod-announce and make a GMOD news item.

As you can tell, this process could really use some more streamlining and automation.


# ===================================================PeakLearner Read Me===================================================

index:
1. Setup
2. Terminology/ About jbrowse
3. Architecture (plugins, functions etc)
4. Refrences

## Setup

First clone the repository found at "https://github.com/yf6666/PeakLearner-1.1". cd in to "PeakLearner-1.1/jbrowse". To inizalize jbrowse you will need to run a script and create a directory inside of jbrowse. first run setup.sh, to run this type in to the terminal "./setup.sh". This may take several minutes, as this makes sure that all nessassary dependencies of jbrowse. This will include downloading perl and nodejs dependencies, as well as some test data called "volvox". Before running the next script create a directory called "data" inside the main jbrowse directory, ie "../PeakLearner-1.1/jbrowse/data".

1. clone repository from "https://github.com/yf6666/PeakLearner-1.1"
2. git checkout <new branch if needed>
3. change directory to "../PeakLearner-1.1/jbrowse"
4. run "./setup.sh"
5. create a directory inside of jbrowse named data, ie "../PeakLearner-1.1/jbrowse/data"

## Terminology/ About jbrowse

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

## Architecture (plugins, functions etc)

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










































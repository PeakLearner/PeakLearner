# PeakLearner-1.1
An Interactive Labeling and model feedback system for genomic data.

## Todos
1. Dynamic model generation and display
2. Authentication system
3. Customizable Hub Upload
4. Better CI

## Building

Web Server:
1. git clone https://github.com/deltarod/PeakLearner-1.1.git
2. cd PeakLearner-1.1/
3. git submodule update --init --recursive - Initializes recursive submodules
4. Install http.server via pip
5. sudo apt update && sudo apt install samtools
6. cd jbrowse
7. ./setup.sh
8. cd ..
9. Install [PeakError](https://github.com/deltarod/PeakError/)
10. python3 run.py

The PeakLearner + Jbrowse webserver should now be started, and can be access at 127.0.0.1:8081.

## Features

UCSCToPeakLearner: A custom dropdown menu which can take a hub.txt file, parse, and create a new data directory for JBrowse to read from.

Interactive Labeling: A user can create, modify, and delete labels for a given track. These labels are then stored on the webserver

## Contributing
Follow the [Contributing Guide](CONTRIBUTING.md)!


# References

Jbrowse Documentation               https://jbrowse.org/docs/installation.html

gmod wiki                           http://gmod.org/wiki/JBrowse

Jbrowse git                         https://github.com/GMOD/jbrowse/

PeakLearner git                     https://github.com/deltarod/PeakLearner-1.1

MultiBigWig git                     https://github.com/elsiklab/multibigwig

WiggleHighlighter git               https://github.com/cmdcolin/wigglehighlighter/issues/1

InteractivePeakAnnotator git        https://github.com/cmdcolin/interactivepeakannotator

PeakLearnerPlugin git               https://github.com/deltarod/PeakLearnerPlugin

PeakError git                       https://github.com/deltarod/PeakError

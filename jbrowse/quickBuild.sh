#!/bin/bash

JBROWSE_BUILD_MIN=${JBROWSE_BUILD_MIN:=1}
# check the exit status of the command, and print the last bit of the log if it fails
done_message () {
    if [ $? == 0 ]; then
        log_echo " done."
        if [ "x$1" != "x" ]; then
            echo $1;
        fi
    else
        echo " failed.  See setup.log file for error messages." $2;
        if [[ "x$3" != "x" ]]; then
            echo "setup cannot continue, aborting.";
            tail -200 setup.log;
            return 1;
        fi
    fi
}

# echoes both to the console, and to setup.log
# adds extra carriage returns in setup.log for readability.
log_echo () {
    echo $@
    echo >> setup.log
    echo $@ >> setup.log
    echo >> setup.log
}

check_node () {
    set +e
    node_executable=$(which node)
    npm_executable=$(which npm)
    if ! [ -x "$node_executable" ] ; then
        nodejs_executable=$(which nodejs)
        if ! [ -x "$nodejs_executable" ] ; then
            echo "No 'node' executable found. JBrowse expects node version 6 or later. Please install an updated version of node.js by following the instructions appropriate for your system https://nodejs.org/en/download/package-manager/";
            return 1
        else
            echo "Creating an alias 'node' for 'nodejs'"
            node_executable="$nodejs_executable"
        fi
    fi
    set -e
    if ! [ -x "$npm_executable" ] ; then
        echo "No 'npm' executable found. JBrowse expects npm version 3 or later. Please install an updated version of node.js by following the instructions appropriate for your system https://nodejs.org/en/download/package-manager/";
        return 1
    fi
    NODE_VERSION=`$node_executable -v`
    NODE_MAJOR_VERSION=`$node_executable -v | cut -dv -f2 | cut -d. -f1`
    NODE_MINOR_VERSION=`$node_executable -v | cut -d. -f1`
    NPM_VERSION=`$npm_executable -v`
    NPM_MAJOR_VERSION=`$npm_executable -v | cut -d. -f1`
    if [[ $NODE_MAJOR_VERSION -lt 6 ]]; then
        echo "node $NODE_VERSION found, but node version 6 or later must be installed.  Please install an updated version of node.js by following the instructions appropriate for your system https://nodejs.org/en/download/package-manager/";
        return 1
    fi
    if [[ $NPM_MAJOR_VERSION -lt 3 ]]; then
        echo "npm $NPM_VERSION found, but npm version 3 or later must be installed.  Please install an updated version of node.js by following the instructions appropriate for your system https://nodejs.org/en/download/package-manager/";
        return 1
    fi
    echo "Node $NODE_VERSION installed at $node_executable with npm $NPM_VERSION";
}

# we are starting a new setup. clear the log file
rm -f setup.log

# log information about this system
log_echo -n "Gathering system information ..."
(
    echo '============== System information ====';
    set -x;
    lsb_release -a;
    uname -a;
    sw_vers;
    grep MemTotal /proc/meminfo;
    echo; echo;
) >>setup.log 2>&1;
done_message "" ""

# check Mac OS version
SUPPRESS_BIODB_TO_JSON=0

sw_vers >& /dev/null;

# if we are running in a development build, then run npm install and run the webpack build.
if [ -f "src/JBrowse/Browser.js" ]; then
    log_echo -n "Installing node.js dependencies and building with webpack ..."
    (
        set -e
        check_node
        [[ -f node_modules/.bin/yarn ]] || npm install yarn
        node_modules/.bin/yarn install
        JBROWSE_BUILD_MIN=$JBROWSE_BUILD_MIN node_modules/.bin/yarn build
    ) >>setup.log 2>&1;
    done_message "" "" "FAILURE NOT ALLOWED"
else
    log_echo "Minimal release, skipping node and Webpack build (note: this version will not allow using plugins. Use a github clone or a dev version of JBrowse to use plugins"
fi



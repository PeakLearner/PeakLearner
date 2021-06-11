#!/bin/sh

cd jbrowse/jbrowse/

yarn run build

cd ../../

uwsgi wsgi.ini
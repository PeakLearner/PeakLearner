#!/bin/sh

tar -cvf screenshots.tar.gz screenshots/

curl --upload-file screenshots.tar.gz https://transfer.sh screenshots.tar.gz
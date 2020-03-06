#!/bin/bash
set -o errexit
R CMD INSTALL .
R -d 'valgrind --track-origins=yes' -e 'library(PeakSegDisk);example(PeakSegFPOP_file)'

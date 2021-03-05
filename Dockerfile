FROM ubuntu as envSetup
ENV TZ="America/Phoenix"
RUN apt-get update
RUN apt-get -y install dialog apt-utils ca-certificates
RUN DEBIAN_FRONTEND="noninteractive" apt-get -y install tzdata
ENV TMPDIR="/home/tem83/tmp/"
RUN apt install -y samtools libdb5.3-dev libdb5.3++-dev git build-essential zlib1g-dev libxml2-dev libexpat-dev npm nano python3-numpy python3-pip
RUN mkdir /build/
WORKDIR /build/
RUN git clone https://github.com/PeakLearner/PeakLearner.git
WORKDIR PeakLearner/
RUN mkdir bin/
ADD http://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64.v385/bigWigSummary bin/
RUN chmod a+x bin/bigWigSummary
RUN git submodule update --init --recursive
WORKDIR jbrowse/jbrowse/
RUN ./setup.sh
WORKDIR ../../
RUN python3 -m pip install -r requirements.txt
RUN python3 -m pip install -e .
CMD ["pserve", "production.ini"]







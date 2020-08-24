mkdir bin
cd bin
curl -OL http://hgdownload.cse.ucsc.edu/admin/exe/linux.x86_64/bigWigInfo
curl -OL http://hgdownload.cse.ucsc.edu/admin/exe/linux.x86_64/bigWigToBedGraph
curl -OL http://hgdownload.cse.ucsc.edu/admin/exe/linux.x86_64/bedToBigBed
curl -OL http://hgdownload.cse.ucsc.edu/admin/exe/linux.x86_64/bedGraphToBigWig
chmod a+x *
mkdir bin
cd bin/
wget http://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64.v385/bigWigToBedGraph
sudo chmod a+x bigWigToBedGraph
cd ../server/
sudo apt install r-base
sudo Rscript -e 'install.packages("data.table")'
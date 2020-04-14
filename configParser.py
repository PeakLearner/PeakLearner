
def printToFile(destination, trackPrints):
   configFile = open(destination, "w")
   configFile.write("[GENERAL]\n")
   configFile.write("refSeqs=hg19.fa.fai\n\n")
   configFile.write(trackPrints)
   configFile.close()

def readInTrack(track):
   splitTrack = track.split('\n')
   trackToReturn = ''
   for i in range(len(splitTrack)):
      splitline = splitTrack[i].split(" ")
      if len(splitline) > 1:
         if splitline[2] == "track":
            trackToReturn += "[tracks." + splitline[-1] + "]\n"
         if splitline[2] == "bigDataUrl":
            trackToReturn += "urlTemplate=" + splitline[-1] + "\n"
         if splitline[2] == "longLabel":
            trackToReturn += "key=" + splitline[-5] + " | " + splitline[-3]+ " | " + splitline[-1] + "\n"
   trackToReturn += "type=InteractivePeakAnnotator/View/Track/XYPlot\n"
   trackToReturn += 'storeConf=json:{"storeClass": "InteractivePeakAnnotator/Store/SeqFeature/Features"}\n\n'
   return trackToReturn

def parseFile(file):
   trackHub = open(file, "r")
   curLine = trackHub.readline()
   trackHolder = ''
   configTracks = ''
   while curLine != '':
      if curLine[1:10] == "autoScale":
         for i in range(7):
            trackHolder += trackHub.readline()
         configTracks += readInTrack(trackHolder)
      trackHolder = ''
      curLine = trackHub.readline()
   trackHub.close()
   return configTracks
   
def main(trackFile, configFile):   
   configPrint = parseFile(trackFile)
   printToFile(configFile, configPrint)
   
main("trackHub.txt", "tracks.conf")


#[tracks.interactive]
#key=interactive
#type=InteractivePeakAnnotator/View/Track/XYPlot
#urlTemplate=volvox_microarray.bw
#storeConf=json:{"storeClass": "InteractivePeakAnnotator/Store/SeqFeature/Features"}

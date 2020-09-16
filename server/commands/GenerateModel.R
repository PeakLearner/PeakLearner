require("PeakSegDisk")

args <- commandArgs(trailingOnly = TRUE)
bigwigUrl <- args[1]
outputPath <- args[2]
chrom <- args[3]
problemStart <- args[4]
problemEnd <- args[5]

Sys.sleep(1)


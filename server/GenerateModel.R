if(!require("PeakSegDisk"))
{
  install.packages("PeakSegDisk")
}

args <- commandArgs(trailingOnly = TRUE)
path <- args[1]
penalty <- args[2]

model <- PeakSegDisk::PeakSegFPOP_file(path, penalty, db.file=tempfile())

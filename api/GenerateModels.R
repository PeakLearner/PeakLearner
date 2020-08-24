# Title     : GenerateModels.R
# Objective : Generates genomic models using PeakSegDisk
# Created by: Tristan
# Created on: 8/24/20

# get dependencies
require("PeakSegDisk")
require("data.table")
library("tools")
# number of penalty values to generate
numPenalties <- 5
penalty.min <- 0
penalty.max <- 10
file.name <- bedFile <- NULL

args <- commandArgs(trailingOnly = TRUE)

# Load File Args
if( length(args) == 0 )
{
    stop("Invalid Number of args")
} else if( length(args) == 1 )
{
    file.name <- args[1]
} else if( length(args) == 4 )
{
    file.name <- args[1]

    numPenalties <- as.numeric(args[2])
    penalty.min <- as.numeric(args[3])
    penalty.max <- as.numeric(args[4])
}

if(penalty.min >= penalty.max)
{
    stop("Minimum Penalty is greater than or equal to maximum penalty")
}

if( penalty.min < 0 )
{
    stop("Minimum penalty values must be greater than 0")
}

if( numPenalties < 1 )
{
    stop("Number of penalty values has a minimum of 3 values")
}

if( !file.exists(file.name) )
{
    stop("File does not exist")
}

file.dir <- dirname(file.name)
file.fName <- basename(file.name)

# if file is currently a bigWig convert it
if( file_ext(file.name) == "bigWig" )
{
    path <- gsub("bigWig", "bigBed", file.fName)

    # Get file name for output bigBed
    bedFile <- paste(file.dir, path, sep='/')

    if( !file.exists(bedFile) )
    {
        # bin/bigWigToBedGraph could probably be less hardcoded
        code <- system(paste("bin/bigWigToBedGraph", file.name, bedFile))

        if( code != 0 )
        {
            stop(paste("Error creating bigBed file:", bedFile))
        }
    }

    file.fName <- path
} else if ( file_ext(file.name) == "bigBed" )
{
    bedFile <- file.name
} else
{
     stop("Invalid File Type")
}

# This section creates a new file for every gap in the bigBed that was just converted
# Get filename for new directory to be created
nogaps.dir <- paste(file.dir, gsub(".bigBed", "", file.fName), sep="/")

if( !dir.exists(nogaps.dir) )
{
    dir.create(nogaps.dir)
}

# TODO: Break down large bigBed file into smaller ones with no gaps

penaltyStep <- ( penalty.max - penalty.min ) / ( numPenalties + 1 )

# Generate evenly spaced penalties between 2 points
penalties <- seq( penalty.min + penaltyStep, penalty.max - penaltyStep, penaltyStep )

# TODO: Multithread this
for( penalty in penalties )
{
    output <- PeakSegFPOP_file(bedFile, toString(penalty))

    print(output)

    #this is here for testing purposes
    return()
}





\name{writeBedGraph}
\alias{writeBedGraph}
\title{Write bedGraph file}
\description{Write a data.frame in R to a bedGraph file on disk. This must be a
plain text file with the following four columns: chrom (character
chromosome name), chromStart (integer start position), chromEnd
(integer end position), count (integer aligned read count on chrom
from chromStart+1 to chromEnd); see also
https://genome.ucsc.edu/goldenPath/help/bedgraph.html}
\usage{writeBedGraph(count.df, 
    coverage.bedGraph)}
\arguments{
  \item{count.df}{data.frame with four columns: chrom, chromStart, chromEnd, count.}
  \item{coverage.bedGraph}{file path where data will be saved in plain text / bedGraph format.}
}

\value{NULL (same as write.table).}

\author{Toby Dylan Hocking}




\examples{

library(PeakSegDisk)
data(Mono27ac, envir=environment())
coverage.bedGraph <- file.path(
  tempfile(),
  "H3K27ac-H3K4me3_TDHAM_BP",
  "samples",
  "Mono1_H3K27ac",
  "S001YW_NCMLS",
  "problems",
  "chr11-60000-580000",
  "coverage.bedGraph")
dir.create(
  dirname(coverage.bedGraph),
  recursive=TRUE, showWarnings=FALSE)
writeBedGraph(Mono27ac$coverage, coverage.bedGraph)
fread.first(coverage.bedGraph, col.name.list$coverage)
fread.last(coverage.bedGraph, col.name.list$coverage)

}

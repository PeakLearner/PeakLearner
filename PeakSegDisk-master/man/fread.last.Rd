\name{fread.last}
\alias{fread.last}
\title{Quickly read last line}
\description{Read the last line of a text file. Useful for quickly checking if
the coverage.bedGraph_penalty=VALUE_segments.bed file is
consistent with the coverage.bedGraph_penalty=VALUE_loss.tsv
file. (used by the \code{\link{PeakSegFPOP_dir}} caching mechanism)}
\usage{fread.last(file.name, 
    col.name.vec)}
\arguments{
  \item{file.name}{Name of file to read.}
  \item{col.name.vec}{Character vector of column names.}
}

\value{Data table with one row.}

\author{Toby Dylan Hocking}




\examples{

library(PeakSegDisk)
r <- function(chrom, chromStart, chromEnd, coverage){
  data.frame(chrom, chromStart, chromEnd, coverage)
}
four <- rbind(
  r("chr1", 0, 10,  2),
  r("chr1", 10, 20, 10),
  r("chr1", 20, 30, 14),
  r("chr1", 30, 40, 13))
write.table(
  four, tmp <- tempfile(),
  sep="\\t", row.names=FALSE, col.names=FALSE)
pstr <- "10.5"
PeakSegFPOP_file(tmp, pstr)

outf <- function(suffix){
  paste0(tmp, "_penalty=", pstr, "_", suffix)
}
segments.bed <- outf("segments.bed")
first.seg.line <- fread.first(segments.bed, col.name.list$segments)
last.seg.line <- fread.last(segments.bed, col.name.list$segments)

loss.tsv <- outf("loss.tsv")
loss.row <- fread.first(loss.tsv, col.name.list$loss)

seg.bases <- first.seg.line$chromEnd - last.seg.line$chromStart
loss.row$bases == seg.bases

}

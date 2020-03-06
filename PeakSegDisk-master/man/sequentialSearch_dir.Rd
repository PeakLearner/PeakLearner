\name{sequentialSearch_dir}
\alias{sequentialSearch_dir}
\title{Compute PeakSeg model with given number of peaks}
\description{Compute the most likely peak model with at most the number of
peaks given by \code{peaks.int}. This function repeated calls
\code{\link{PeakSegFPOP_dir}} with different penalty values, until either
(1) it finds the \code{peaks.int} model, or (2) it concludes that there
is no \code{peaks.int} model, in which case it returns the next simplest
model (with fewer peaks than \code{peaks.int}).
The first pair of penalty values (0, Inf) is run in parallel
via the user-specified future plan,
if the future.apply package is available.}
\usage{sequentialSearch_dir(problem.dir, 
    peaks.int, verbose = 0)}
\arguments{
  \item{problem.dir}{problemID directory in which coverage.bedGraph has already been
computed. If there is a labels.bed file then the number of
incorrect labels will be computed in order to find the target
interval of minimal error penalty values.}
  \item{peaks.int}{int: target number of peaks.}
  \item{verbose}{numeric verbosity: if >0 then \code{\link[base]{cat}} is used to print a message
for each penalty.}
}

\value{Same result list from \code{\link{PeakSegFPOP_dir}}, with an additional
component "others" describing the other models that were computed
before finding the optimal model with \code{peaks.int} (or fewer)
peaks. Additional loss columns are as follows: under=number of
peaks in smaller model during binary search; over=number of peaks
in larger model during binary search; iteration=number of times
PeakSegFPOP has been run.}

\author{Toby Dylan Hocking}




\examples{

## Create simple 6 point data set discussed in supplementary
## materials. GFPOP/GPDPA computes up-down model with 2 peaks, but
## neither CDPA (PeakSegDP::cDPA) nor PDPA (jointseg)
r <- function(chrom, chromStart, chromEnd, coverage){
  data.frame(chrom, chromStart, chromEnd, coverage)
}
supp <- rbind(
  r("chr1", 0, 1,  3),
  r("chr1", 1, 2, 9),
  r("chr1", 2, 3, 18),
  r("chr1", 3, 4, 15),
  r("chr1", 4, 5, 20),
  r("chr1", 5, 6, 2)
)
data.dir <- file.path(tempfile(), "chr1-0-6")
dir.create(data.dir, recursive=TRUE)
write.table(
  supp, file.path(data.dir, "coverage.bedGraph"),
  sep="\\t", row.names=FALSE, col.names=FALSE)

## register a parallel future plan to compute the first two
## penalties in parallel during the sequential search.
if(interactive() && requireNamespace("future"))future::plan("multiprocess")

## Compute optimal up-down model with 2 peaks via sequential search.
fit <- PeakSegDisk::sequentialSearch_dir(data.dir, 2L)

library(ggplot2)
ggplot()+
  theme_bw()+
  geom_point(aes(
    chromEnd, coverage),
    data=supp)+
  geom_segment(aes(
    chromStart+0.5, mean,
    xend=chromEnd+0.5, yend=mean),
    data=fit$segments,
    color="green")

}

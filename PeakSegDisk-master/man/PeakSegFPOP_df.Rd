\name{PeakSegFPOP_df}
\alias{PeakSegFPOP_df}
\title{PeakSeg penalized solver for data.frame}
\description{Write data frame to disk then run \code{\link{PeakSegFPOP_dir}} solver.}
\usage{PeakSegFPOP_df(count.df, 
    pen.num, base.dir = tempdir())}
\arguments{
  \item{count.df}{data.frame with columns count, chromStart, chromEnd. These data
will be saved via \code{\link{writeBedGraph}}, creating a plain text file with
the following four columns: chrom (character chromosome name),
chromStart (integer start position), chromEnd (integer end
position), count (integer aligned read count on chrom from
chromStart+1 to chromEnd); see also
https://genome.ucsc.edu/goldenPath/help/bedgraph.html}
  \item{pen.num}{Non-negative numeric scalar.}
  \item{base.dir}{base.dir/chrXX-start-end/coverage.bedGraph will be written, where
chrXX is the chrom column, start is the first chromStart position,
and end is the last chromEnd position.}
}

\value{List of solver results, same as \code{\link{PeakSegFPOP_dir}}.}

\author{Toby Dylan Hocking}




\examples{

## Simulate a sequence of Poisson count data.
sim.seg <- function(seg.mean, size.mean=15){
  seg.size <- rpois(1, size.mean)
  rpois(seg.size, seg.mean)
}
set.seed(1)
seg.mean.vec <- c(1.5, 3.5, 0.5, 4.5, 2.5)
z.list <- lapply(seg.mean.vec, sim.seg)
z.rep.vec <- unlist(z.list)

## Plot the simulated data sequence.
library(ggplot2)
count.df <- data.frame(
  position=seq_along(z.rep.vec),
  count=z.rep.vec)
gg.count <- ggplot()+
  geom_point(aes(
    position, count),
    shape=1,
    data=count.df)
gg.count

## Plot the true changes.
n.segs <- length(seg.mean.vec)
seg.size.vec <- sapply(z.list, length)
seg.end.vec <- cumsum(seg.size.vec)
change.vec <- seg.end.vec[-n.segs]+0.5
change.df <- data.frame(
  changepoint=change.vec)
gg.change <- gg.count+
  geom_vline(aes(
    xintercept=changepoint),
    data=change.df)
gg.change

## Plot the run-length encoding of the same data.
z.rle.vec <- rle(z.rep.vec)
chromEnd <- cumsum(z.rle.vec$lengths)
coverage.df <- data.frame(
  chrom="chrUnknown",
  chromStart=c(0L, chromEnd[-length(chromEnd)]),
  chromEnd,
  count=z.rle.vec$values)
gg.rle <- gg.change+
  geom_segment(aes(
    chromStart+0.5, count, xend=chromEnd+0.5, yend=count),
    data=coverage.df)
gg.rle

## Fit a peak model and plot the segment means.
fit <- PeakSegDisk::PeakSegFPOP_df(coverage.df, 10.5)
gg.rle+
  geom_segment(aes(
    chromStart+0.5, mean, xend=chromEnd+0.5, yend=mean),
    color="green",
    data=fit$segments)

## Default plot method shows data as geom_step.
(gg <- plot(fit))

## Plot data as points to verify the step representation.
gg+
  geom_point(aes(
    position, count),
    color="grey",
    shape=1,
    data=count.df)

}

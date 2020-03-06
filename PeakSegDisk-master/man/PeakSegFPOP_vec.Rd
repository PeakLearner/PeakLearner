\name{PeakSegFPOP_vec}
\alias{PeakSegFPOP_vec}
\title{PeakSeg penalized solver for integer vector}
\description{Convert integer data vector to run-length encoding,
then run \code{\link{PeakSegFPOP_df}}.}
\usage{PeakSegFPOP_vec(count.vec, 
    pen.num)}
\arguments{
  \item{count.vec}{integer vector, noisy non-negatve count data to segment.}
  \item{pen.num}{Non-negative numeric scalar.}
}

\value{List of solver results, same as \code{\link{PeakSegFPOP_dir}}.}

\author{Toby Dylan Hocking}




\examples{

## Simulate a sequence of Poisson data.
sim.seg <- function(seg.mean, size.mean=15){
  seg.size <- rpois(1, size.mean)
  rpois(seg.size, seg.mean)
}
set.seed(1)
seg.mean.vec <- c(1.5, 3.5, 0.5, 4.5, 2.5)
z.list <- lapply(seg.mean.vec, sim.seg)
z.rep.vec <- unlist(z.list)

## Plot the simulated data.
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

## Plot the true changepoints.
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

## Fit a peak model and plot it.
fit <- PeakSegDisk::PeakSegFPOP_vec(z.rep.vec, 10.5)
gg.change+
  geom_segment(aes(
    chromStart+0.5, mean, xend=chromEnd+0.5, yend=mean),
    color="green",
    data=fit$segments)

## A pathological data set.
z.slow.vec <- 1:length(z.rep.vec)
fit.slow <- PeakSegDisk::PeakSegFPOP_vec(z.slow.vec, 10.5)
rbind(fit.slow$loss, fit$loss)

}

PeakSegFPOP_vec <- structure(function # PeakSeg penalized solver for integer vector
### Convert integer data vector to run-length encoding,
### then run PeakSegFPOP_df.
(count.vec,
### integer vector, noisy non-negatve count data to segment.
  pen.num
### Non-negative numeric scalar.
){
  if(!(
    is.numeric(pen.num) &&
    length(pen.num)==1 &&
    0 <= pen.num)){
    stop("pen.num must be non-negative numeric scalar")
  }
  if(!is.integer(count.vec)){
    stop("count.vec must be integer")
  }
  z.rle.vec <- rle(count.vec)
  chromEnd <- cumsum(z.rle.vec$lengths)
  coverage.df <- data.frame(
    chrom="chrUnknown",
    chromStart=c(0L, chromEnd[-length(chromEnd)]),
    chromEnd,
    count=z.rle.vec$values)
  PeakSegFPOP_df(coverage.df, pen.num)
### List of solver results, same as PeakSegFPOP_dir.
}, ex=function(){

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

})


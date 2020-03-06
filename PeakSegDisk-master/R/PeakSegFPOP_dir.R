PeakSegFPOP_dir <- structure(function # PeakSeg penalized solver with caching
### Main function/interface for the PeakSegDisk package.
### Run the low-level solver, PeakSegFPOP_file,
### on one genomic segmentation problem
### directory, and read the result files into R. Actually, this
### function will first check if the result files are already present
### (and consistent), and if so, it will simply read them into R
### (without running PeakSegFPOP_file) -- this is a caching mechanism
### that can save a lot of time.
### To run the algo on an integer vector, use PeakSegFPOP_vec;
### for a data.frame, use PeakSegFPOP_df.
### To compute the optimal model for a given number of peaks,
### use sequentialSearch_dir.
(problem.dir,
### Path to a directory like sampleID/problems/chrXX-start-end which
### contains a coverage.bedGraph file with the aligned read counts for
### one genomic segmentation problem. This must be a plain text file
### with the following four columns: chrom (character chromosome
### name), chromStart (integer start position), chromEnd (integer end
### position), count (integer aligned read count on chrom from
### chromStart+1 to chromEnd); see also
### https://genome.ucsc.edu/goldenPath/help/bedgraph.html. Note that
### the standard coverage.bedGraph file name is required; for full
### flexibility the user can run the algo on an arbitrarily named file
### via PeakSegFPOP_file (see that man page for an explanation of how
### storage on disk happens).
 penalty.param,
### non-negative numeric penalty parameter (larger values for fewer
### peaks), or character scalar which can be interpreted as such. 0
### means max peaks, Inf means no peaks.
  db.file=NULL
### character scalar: file for writing temporary cost function
### database -- there will be a lot of disk writing to this
### file. Default NULL means to write the same disk where the input
### bedGraph file is stored; another option is tempfile() which may
### result in speedups if the input bedGraph file is on a slow network
### disk and the temporary storage is a fast local disk.
){
  megabytes <- NULL
  ##details<< Finds the optimal change-points using the Poisson loss
  ## and the PeakSeg constraint (changes in mean alternate between
  ## non-decreasing and non-increasing). For \eqn{N} data points, the
  ## functional pruning algorithm is \eqn{O(\log N)} memory. It is
  ## \eqn{O(N \log N)} time and disk space. It computes the
  ## exact solution to the optimization problem in
  ## \code{vignette("Examples", package="PeakSegDisk")}.
  if(!(
    is.character(problem.dir) &&
    length(problem.dir)==1 &&
    dir.exists(problem.dir))){
    stop(
      "problem.dir=", problem.dir,
      " must be the name of a directory",
      " containing a file named coverage.bedGraph")
  }
  ##alias<< PeakSegDisk
  if(!(
    (is.numeric(penalty.param) || is.character(penalty.param)) &&
    length(penalty.param)==1 &&
    (!is.na(penalty.param))
  )){
    stop("penalty.param must be numeric or character, length 1, not missing")
  }
  penalty.str <- paste(penalty.param)
  prob.cov.bedGraph <- file.path(problem.dir, "coverage.bedGraph")
  pre <- paste0(prob.cov.bedGraph, "_penalty=", penalty.str)
  penalty_segments.bed <- paste0(pre, "_segments.bed")
  penalty_loss.tsv <- paste0(pre, "_loss.tsv")
  penalty_timing.tsv <- paste0(pre, "_timing.tsv")
  already.computed <- tryCatch({
    timing <- fread(
      file=penalty_timing.tsv,
      col.names=c("penalty", "megabytes", "seconds"))
    first.seg.line <- fread.first(penalty_segments.bed, col.name.list$segments)
    last.seg.line <- fread.last(penalty_segments.bed, col.name.list$segments)
    first.cov.line <- fread.first(prob.cov.bedGraph, col.name.list$coverage)
    last.cov.line <- fread.last(prob.cov.bedGraph, col.name.list$coverage)
    penalty.loss <- fread(file=penalty_loss.tsv, col.names=col.name.list$loss)
    nrow.ok <- nrow(timing)==1 && nrow(penalty.loss)==1 &&
      nrow(first.seg.line)==1 && nrow(last.seg.line)==1 &&
      nrow(first.cov.line)==1 && nrow(last.cov.line)==1
    loss.segments.consistent <-
      first.seg.line$chromEnd-last.seg.line$chromStart == penalty.loss$bases
    ## segments files are written by decoding/backtracking after
    ## dynamic progamming, so it is normal that the first line of the
    ## segment file is actually the last segment in terms of position
    ## on the chromosome.
    start.ok <- first.cov.line$chromStart == last.seg.line$chromStart
    end.ok <- last.cov.line$chromEnd == first.seg.line$chromEnd
    nrow.ok && loss.segments.consistent && start.ok && end.ok
  }, error=function(e){
    FALSE
  })
  if(!already.computed){
    seconds <- system.time({
      result <- PeakSegFPOP_file(prob.cov.bedGraph, penalty.str, db.file)
    })[["elapsed"]]
    timing <- data.table(
      penalty=as.numeric(penalty.str),
      megabytes=result$megabytes,
      seconds)
    write.table(
      timing,
      penalty_timing.tsv,
      row.names=FALSE, col.names=FALSE,
      quote=FALSE, sep="\t")
    penalty.loss <- fread(file=penalty_loss.tsv, col.names=col.name.list$loss)
  }
  penalty.segs <- fread(
    file=penalty_segments.bed, col.names=col.name.list$segments)
  L <- list(
    segments=penalty.segs,
    loss=data.table(
      penalty.loss,
      timing[, list(megabytes, seconds)]))
  class(L) <- c("PeakSegFPOP_dir", "list")
  L
### Named list of two data.tables:
### \item{segments}{has one row for every segment in the optimal model,}
### \item{loss}{has one row and contains the following columns:}
### \describe{
### \item{penalty}{same as input parameter}
### \item{segments}{number of segments in optimal model}
### \item{peaks}{number of peaks in optimal model}
### \item{bases}{number of positions described in bedGraph file}
### \item{bedGraph.lines}{number of lines in bedGraph file}
### \item{total.loss}{total Poisson loss
###   = \eqn{\sum_i m_i-z_i*\log(m_i)} =
###   mean.pen.cost*bases-penalty*peaks}
### \item{mean.pen.cost}{mean penalized cost = (total.loss+penalty*peaks)/bases}
### \item{equality.constraints}{number of adjacent segment means that have
###   equal values in the optimal solution}
### \item{mean.intervals}{mean number of intervals/candidate
###   changepoints stored in optimal cost functions -- useful for
###   characterizing the computational complexity of the algorithm}
### \item{max.intervals}{maximum number of intervals}
### \item{megabytes}{disk usage of *.db file}
### \item{seconds}{timing of PeakSegFPOP_file}
### }
}, ex=function(){

  data(Mono27ac, package="PeakSegDisk", envir=environment())
  data.dir <- file.path(
    tempfile(),
    "H3K27ac-H3K4me3_TDHAM_BP",
    "samples",
    "Mono1_H3K27ac",
    "S001YW_NCMLS",
    "problems",
    "chr11-60000-580000")
  dir.create(data.dir, recursive=TRUE, showWarnings=FALSE)
  write.table(
    Mono27ac$coverage, file.path(data.dir, "coverage.bedGraph"),
    col.names=FALSE, row.names=FALSE, quote=FALSE, sep="\t")

  ## Compute one model with penalty=1952.6
  (fit <- PeakSegDisk::PeakSegFPOP_dir(data.dir, 1952.6))
  summary(fit)#same as fit$loss

  ## Visualize that model.
  ann.colors <- c(
    noPeaks="#f6f4bf",
    peakStart="#ffafaf",
    peakEnd="#ff4c4c",
    peaks="#a445ee")
  library(ggplot2)
  lab.min <- Mono27ac$labels[1, chromStart]
  lab.max <- Mono27ac$labels[.N, chromEnd]

  plist <- coef(fit)
  gg <- ggplot()+
    theme_bw()+
    geom_rect(aes(
      xmin=chromStart/1e3, xmax=chromEnd/1e3,
      ymin=-Inf, ymax=Inf,
      fill=annotation),
      color="grey",
      alpha=0.5,
      data=Mono27ac$labels)+
    scale_fill_manual("label", values=ann.colors)+
    geom_step(aes(
      chromStart/1e3, count),
      color="grey50",
      data=Mono27ac$coverage)+
    geom_segment(aes(
      chromStart/1e3, mean,
      xend=chromEnd/1e3, yend=mean),
      color="green",
      size=1,
      data=plist$segments)+
    geom_vline(aes(
      xintercept=chromEnd/1e3, linetype=constraint),
      color="green",
      data=plist$changes)+
    scale_linetype_manual(
      values=c(
        inequality="dotted",
        equality="solid"))
  gg

  gg+
    coord_cartesian(xlim=c(lab.min, lab.max)/1e3, ylim=c(0, 10))

  ## Default plotting method only shows model.
  (gg <- plot(fit))

  ## Data can be added on top of model.
  gg+
    geom_step(aes(
      chromStart, count),
      color="grey50",
      data=Mono27ac$coverage)

})

### Compute changes and peaks to display/plot.
coef.PeakSegFPOP_dir <- function(object, ...){
  chromEnd <- status <- NULL
  ## above to avoid CRAN check NOTE.
  object$changes <- object$segments[, list(
    type="segmentation",
    constraint=ifelse(
      diff(mean)==0, "equality", "inequality"),
    chromEnd=chromEnd[-1])]
  object$peaks <- data.table(
    type="peaks",
    object$segments[status=="peak"])
  object$segments <- data.table(type="segmentation", object$segments)
  object
### model list with additional named elements peaks and changes.
}

### Summary of PeakSegFPOP_dir object.
summary.PeakSegFPOP_dir <- function(object, ...){
  object$loss
### Data table with one row and columns describing model summary.
}

### Plot a PeakSeg model with attached data.
plot.PeakSegFPOP_dir <- function(x, ...){
  chromStart <- type <- chromEnd <- constraint <- NULL
  ## above to avoid CRAN check NOTE.
  if(!requireNamespace("ggplot2")){
    stop("install ggplot2 for plotting functionality")
  }
  L <- coef(x)
  ggplot2::ggplot()+
    ggplot2::theme_bw()+
    ggplot2::scale_color_manual(values=c(
      data="grey50",
      peaks="deepskyblue",
      segmentation="green"
    ))+
    ggplot2::geom_segment(ggplot2::aes(
      chromStart+0.5, mean,
      color=type,
      xend=chromEnd+0.5, yend=mean),
      size=1,
      data=L$segments)+
    ggplot2::geom_segment(ggplot2::aes(
      chromStart+0.5, Inf,
      color=type,
      xend=chromEnd+0.5, yend=Inf),
      size=2,
      data=L$peaks)+
    ggplot2::geom_point(ggplot2::aes(
      chromStart+0.5, Inf,
      color=type),
      shape=1,
      size=2,
      data=L$peaks)+
    ggplot2::geom_vline(ggplot2::aes(
      xintercept=chromEnd+0.5,
      color=type,
      linetype=constraint),
      data=L$changes)+
    ggplot2::scale_linetype_manual(
      values=c(
        inequality="dotted",
        equality="solid"))+
    ggplot2::xlab("position")
### a ggplot.
}


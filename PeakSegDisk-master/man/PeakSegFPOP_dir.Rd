\name{PeakSegFPOP_dir}
\alias{PeakSegFPOP_dir}
\alias{PeakSegDisk}
\title{PeakSeg penalized solver with caching}
\description{Main function/interface for the PeakSegDisk package.
Run the low-level solver, \code{\link{PeakSegFPOP_file}},
on one genomic segmentation problem
directory, and read the result files into R. Actually, this
function will first check if the result files are already present
(and consistent), and if so, it will simply read them into R
(without running \code{\link{PeakSegFPOP_file}}) -- this is a caching mechanism
that can save a lot of time.
To run the algo on an integer vector, use \code{\link{PeakSegFPOP_vec}};
for a data.frame, use \code{\link{PeakSegFPOP_df}}.
To compute the optimal model for a given number of peaks,
use \code{\link{sequentialSearch_dir}}.}
\usage{PeakSegFPOP_dir(problem.dir, 
    penalty.param, db.file = NULL)}
\arguments{
  \item{problem.dir}{Path to a directory like sampleID/problems/chrXX-start-end which
contains a coverage.bedGraph file with the aligned read counts for
one genomic segmentation problem. This must be a plain text file
with the following four columns: chrom (character chromosome
name), chromStart (integer start position), chromEnd (integer end
position), count (integer aligned read count on chrom from
chromStart+1 to chromEnd); see also
https://genome.ucsc.edu/goldenPath/help/bedgraph.html. Note that
the standard coverage.bedGraph file name is required; for full
flexibility the user can run the algo on an arbitrarily named file
via \code{\link{PeakSegFPOP_file}} (see that man page for an explanation of how
storage on disk happens).}
  \item{penalty.param}{non-negative numeric penalty parameter (larger values for fewer
peaks), or character scalar which can be interpreted as such. 0
means max peaks, Inf means no peaks.}
  \item{db.file}{character scalar: file for writing temporary cost function
database -- there will be a lot of disk writing to this
file. Default NULL means to write the same disk where the input
bedGraph file is stored; another option is tempfile() which may
result in speedups if the input bedGraph file is on a slow network
disk and the temporary storage is a fast local disk.}
}
\details{Finds the optimal change-points using the Poisson loss
and the PeakSeg constraint (changes in mean alternate between
non-decreasing and non-increasing). For \eqn{N} data points, the
functional pruning algorithm is \eqn{O(\log N)} memory. It is
\eqn{O(N \log N)} time and disk space. It computes the
exact solution to the optimization problem in
\code{vignette("Examples", package="PeakSegDisk")}.}
\value{Named list of two data.tables:
\item{segments}{has one row for every segment in the optimal model,}
\item{loss}{has one row and contains the following columns:}
\describe{
\item{penalty}{same as input parameter}
\item{segments}{number of segments in optimal model}
\item{peaks}{number of peaks in optimal model}
\item{bases}{number of positions described in bedGraph file}
\item{bedGraph.lines}{number of lines in bedGraph file}
\item{total.loss}{total Poisson loss
= \eqn{\sum_i m_i-z_i*\log(m_i)} =
mean.pen.cost*bases-penalty*peaks}
\item{mean.pen.cost}{mean penalized cost = (total.loss+penalty*peaks)/bases}
\item{equality.constraints}{number of adjacent segment means that have
equal values in the optimal solution}
\item{mean.intervals}{mean number of intervals/candidate
changepoints stored in optimal cost functions -- useful for
characterizing the computational complexity of the algorithm}
\item{max.intervals}{maximum number of intervals}
\item{megabytes}{disk usage of *.db file}
\item{seconds}{timing of PeakSegFPOP_file}
}}

\author{Toby Dylan Hocking}




\examples{

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
  col.names=FALSE, row.names=FALSE, quote=FALSE, sep="\\t")

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

}

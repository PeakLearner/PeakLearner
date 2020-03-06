\name{ChIPreads}
\alias{ChIPreads}
\docType{data}
\title{
  Reads aligned to hg19 from two ChIP-seq experiments
}
\description{
  These data are raw aligned reads which have been mapped to the human
  genome, hg19. One is sample ID McGill0004, experiment H3K36me3, chr9,
  chunk H3K36me3_AM_immune/8. The other is sample ID McGill0002,
  experiment H3K4me3, chr2, chunk H3K4me3_PGP_immune/7.
  The chunk ID numbers refer to parts of the McGill benchmark data set,
  \url{http://members.cbio.mines-paristech.fr/~thocking/chip-seq-chunk-db/}
}
\usage{data("ChIPreads")}
\format{
  A data frame with 40396 observations on the following 4 variables.
  \describe{
    \item{\code{experiment}}{either H3K36me3 or H3K4me3}
    \item{\code{chrom}}{either chr9 or chr2}
    \item{\code{chromStart}}{0-based start position of read}
    \item{\code{chromEnd}}{1-based end position of read}
    \item{\code{count}}{number of times a read occured with the given
      chromStart/end in this sample/experiment}
  }
}
\details{
  Peak detection algorithm are typically run on a sequence of
  non-negative integer
  count data, one data point for each genomic position.
  These data are useful for proving that peak detection methods are
  robust to different sequences: (1) spatially correlated,
  non-independent aligned read coverage; (2) un-correlated, independent
  representations such as first or last read.
}
\keyword{datasets}

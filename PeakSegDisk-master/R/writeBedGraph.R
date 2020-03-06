writeBedGraph <- structure(function # Write bedGraph file
### Write a data.frame in R to a bedGraph file on disk. This must be a
### plain text file with the following four columns: chrom (character
### chromosome name), chromStart (integer start position), chromEnd
### (integer end position), count (integer aligned read count on chrom
### from chromStart+1 to chromEnd); see also
### https://genome.ucsc.edu/goldenPath/help/bedgraph.html
(count.df,
### data.frame with four columns: chrom, chromStart, chromEnd, count.
  coverage.bedGraph
### file path where data will be saved in plain text / bedGraph format.
){
  if(!is.data.frame(count.df)){
    stop("count.df must be data.frame")
  }
  exp.names <- c("chrom", "chromStart", "chromEnd", "count")
  if(!identical(names(count.df), exp.names)){
    stop("count.df must have names ", paste(exp.names, collapse=", "))
  }
  if(!is.integer(count.df$chromStart)){
    stop("count.df$chromStart must be integer")
  }
  if(!is.integer(count.df$chromEnd)){
    stop("count.df$chromEnd must be integer")
  }
  if(!is.numeric(count.df$count)){
    stop("count.df$count must be numeric")
  }
  if(any(count.df$chromStart < 0)){
    stop("count.df$chromStart must always be non-negative")
  }
  if(!all(count.df$chromStart < count.df$chromEnd)){
    stop("chromStart must be less than chromEnd for all rows of count.df")
  }
  write.table(
    count.df, coverage.bedGraph,
    quote=FALSE, sep="\t", row.names=FALSE, col.names=FALSE)
### NULL (same as write.table).
}, ex=function(){

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

})

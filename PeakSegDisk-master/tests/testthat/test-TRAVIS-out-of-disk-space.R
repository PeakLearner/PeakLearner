library(testthat)
context("out of disk space")
library(PeakSegDisk)
library(data.table)
data(Mono27ac)

## This test relies on the existence of this very small 200K
## filesystem mounted on /tmp/tmp200K
tmp.dir <- "/tmp/tmp200K"
if(!dir.exists(tmp.dir)){
  dir.create(tmp.dir)
  system("sudo mount -t tmpfs -o size=200K tmpfs /tmp/tmp200K")
}
unlink(file.path(tmp.dir, "*"), recursive=TRUE)
data.dir <- file.path(
  tmp.dir,
  "H3K27ac-H3K4me3_TDHAM_BP",
  "samples",
  "Mono1_H3K27ac",
  "S001YW_NCMLS",
  "problems",
  "chr11-60000-580000")
dir.create(data.dir, recursive=TRUE, showWarnings=FALSE)
labels.bed <- file.path(data.dir, "labels.bed")
coverage.bedGraph <- file.path(data.dir, "coverage.bedGraph")
fwrite(
  Mono27ac$labels, labels.bed,
  col.names=FALSE, row.names=FALSE, quote=FALSE, sep="\t")
fwrite(
  Mono27ac$coverage, coverage.bedGraph,
  col.names=FALSE, row.names=FALSE, quote=FALSE, sep="\t")
(du.dt <- fread(
  paste("du -bs", file.path(data.dir, "*")),
  col.names=c("bytes", "file")))
system(paste("du -bs", tmp.dir))

test_that("PeakSegFPOP_dir error writing cost function database", {
  expect_error({
    PeakSegFPOP_dir(data.dir, 0)
  }, "unable to write to cost function database file")
})

size <- sum(du.dt$bytes)*1.5
tmp.dir <- paste0("/tmp/tmp", size)
if(!file.exists(tmp.dir)){
  cmd <- paste0(
    "mkdir ",
    tmp.dir,
    "&& sudo mount -t tmpfs -o size=",
    size,
    " tmpfs ",
    tmp.dir)
  system(cmd)
}
## This test should gracefully fail writing the segments file during
## decoding.
unlink(file.path(tmp.dir, "*"), recursive=TRUE)
data.dir <- file.path(
  tmp.dir,
  "H3K27ac-H3K4me3_TDHAM_BP",
  "samples",
  "Mono1_H3K27ac",
  "S001YW_NCMLS",
  "problems",
  "chr11-60000-580000")
dir.create(data.dir, recursive=TRUE, showWarnings=FALSE)
labels.bed <- file.path(data.dir, "labels.bed")
coverage.bedGraph <- file.path(data.dir, "coverage.bedGraph")
fwrite(
  Mono27ac$labels, labels.bed,
  col.names=FALSE, row.names=FALSE, quote=FALSE, sep="\t")
fwrite(
  Mono27ac$coverage, coverage.bedGraph,
  col.names=FALSE, row.names=FALSE, quote=FALSE, sep="\t")
getbytes <- function(){
  fread(
    paste("du -bs", data.dir),
    col.names=c("bytes", "file"))$bytes
}
old.bytes <- 0
while(old.bytes != (new.bytes <- getbytes())){
  old.bytes <- new.bytes
  fwrite(
    Mono27ac$coverage, file.path(data.dir, "filler"),
    col.names=FALSE, row.names=FALSE, quote=FALSE, sep="\t")
}

test_that("PeakSegFPOP_file error writing loss output", {
  expect_error({
    L <- PeakSegFPOP_file(
      file.path(data.dir, "coverage.bedGraph"),
      "Inf")#Inf does not write a cost function db.
  }, "unable to write to loss output file")
})

new.du.dt <- fread(paste("du -bs", file.path(data.dir, "*")))
setnames(new.du.dt, c("bytes", "file"))
new.du.dt[, list(bytes, file=sub(".*/", "", file))]

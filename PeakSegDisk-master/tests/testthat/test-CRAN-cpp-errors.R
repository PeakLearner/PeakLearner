library(testthat)
context("cpp-errors")
library(PeakSegDisk)

bg.file <- tempfile()
db.file <- tempfile()
cat("chr1 0 1 5\nchr1 1 3 3", file=bg.file)
test_that("finite penalty returns list", {
  L <- .C(
    "PeakSegFPOP_interface",
    bedGraph.file=bg.file,
    penalty="0.1",
    db.file=db.file,
    PACKAGE="PeakSegDisk")
  expect_is(L, "list")
})

test_that("Inf penalty returns list", {
  L <- .C(
    "PeakSegFPOP_interface",
    bedGraph.file=bg.file,
    penalty="Inf",
    db.file=db.file,
    PACKAGE="PeakSegDisk")
  expect_is(L, "list")
})

test_that("error for non-numeric penalty", {
  expect_error({
    .C(
      "PeakSegFPOP_interface",
      bedGraph.file=bg.file,
      penalty="foobar",
      db.file=db.file,
      PACKAGE="PeakSegDisk")
  }, "penalty string 'foobar' is not numeric; it should be convertible to double")
})

test_that("error for NAN penalty", {
  expect_error({
    .C(
      "PeakSegFPOP_interface",
      bedGraph.file=bg.file,
      penalty="NAN",
      db.file=db.file,
      PACKAGE="PeakSegDisk")
  }, "penalty=NAN but must be finite")
})

test_that("error for negative penalty", {
  expect_error({
    .C(
      "PeakSegFPOP_interface",
      bedGraph.file=bg.file,
      penalty="-0.1",
      db.file=db.file,
      PACKAGE="PeakSegDisk")
  }, "penalty=-0.1 must be non-negative")
})

test_that("error for file that does not exist", {
  expect_error({
    .C(
      "PeakSegFPOP_interface",
      bedGraph.file=tempfile(),
      penalty="0.1",
      db.file=db.file,
      PACKAGE="PeakSegDisk")
  }, "unable to open input file for reading")
})

three.file <- tempfile()
cat("0 1 5\n1 3 3", file=three.file)
test_that("error for three column data file", {
  expect_error({
    .C(
      "PeakSegFPOP_interface",
      bedGraph.file=three.file,
      penalty="0.1",
      db.file=db.file,
      PACKAGE="PeakSegDisk")
  }, "should have exactly four columns")
})

dbl.file <- tempfile()
cat("chr1 0 1 5\nchr1 1 3 3.2", file=dbl.file)
test_that("error for non-integer data", {
  expect_error({
    .C(
      "PeakSegFPOP_interface",
      bedGraph.file=dbl.file,
      penalty="0.1",
      db.file=db.file,
      PACKAGE="PeakSegDisk")
  }, "should be integer")
})

gap.file <- tempfile()
cat("chr1 0 1 5\nchr1 2 3 3", file=gap.file)
test_that("error for non-integer data", {
  expect_error({
    .C(
      "PeakSegFPOP_interface",
      bedGraph.file=gap.file,
      penalty="0.1",
      db.file=db.file,
      PACKAGE="PeakSegDisk")
  }, "there should be no gaps")
})

empty.file <- tempfile()
cat("", file=empty.file)
test_that("error for no data", {
  expect_error({
    .C(
      "PeakSegFPOP_interface",
      bedGraph.file=empty.file,
      penalty="0.1",
      db.file=db.file,
      PACKAGE="PeakSegDisk")
  }, "no data")
})

noseg.file <- tempfile()
cat("chr1 0 1 5\nchr1 1 3 3", file=noseg.file)
pen.str <- "0.1"
seg.file <- paste0(noseg.file, "_penalty=", pen.str, "_segments.bed")
dir.create(seg.file)
test_that("error if segments file unwritable", {
  expect_error({
    .C(
      "PeakSegFPOP_interface",
      bedGraph.file=noseg.file,
      penalty=pen.str,
      db.file=db.file,
      PACKAGE="PeakSegDisk")
  }, "unable to write to segments output file")
})

noloss.file <- tempfile()
cat("chr1 0 1 5\nchr1 1 3 3", file=noloss.file)
pen.str <- "0.1"
loss.file <- paste0(noloss.file, "_penalty=", pen.str, "_loss.tsv")
dir.create(loss.file)
test_that("error if loss file unwritable", {
  expect_error({
    .C(
      "PeakSegFPOP_interface",
      bedGraph.file=noloss.file,
      penalty=pen.str,
      db.file=db.file,
      PACKAGE="PeakSegDisk")
  }, "unable to write to loss output file")
})

nodb.file <- tempfile()
cat("chr1 0 1 5\nchr1 1 3 3", file=nodb.file)
pen.str <- "0.1"
db.file <- paste0(nodb.file, "_penalty=", pen.str, ".db")
dir.create(db.file)
test_that("error if db file unwritable", {
  expect_error({
    .C(
      "PeakSegFPOP_interface",
      bedGraph.file=nodb.file,
      penalty=pen.str,
      db.file=db.file,
      PACKAGE="PeakSegDisk")
  }, "unable to write to cost function database file")
})

test_that("error if first arg non-char", {
  expect_error({
    .C(
      "PeakSegFPOP_interface",
      bedGraph.file=TRUE,
      penalty=pen.str,
      db.file=db.file,
      PACKAGE="PeakSegDisk")
  }, "wrong type for argument 1")
})

test_that("error if second arg non-char", {
  expect_error({
    .C(
      "PeakSegFPOP_interface",
      bedGraph.file="foobar",
      penalty=0.1,
      db.file=db.file,
      PACKAGE="PeakSegDisk")
  }, "wrong type for argument 2")
})

test_that("error if third arg non-char", {
  expect_error({
    .C(
      "PeakSegFPOP_interface",
      bedGraph.file="foobar",
      penalty="sars",
      db.file=0.1,
      PACKAGE="PeakSegDisk")
  }, "wrong type for argument 3")
})

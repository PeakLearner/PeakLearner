library(testthat)
library(PeakSegDisk)
context("wc2int")

test_that("wc2int works with initial space", {
  n.lines <- wc2int("    6921 /var/folders/7j/bq7gdv517tv9bb54j2tfnt3w0000gn/T//Rtmpu71VKi/file363125abb95f/H3K27ac-H3K4me3_TDHAM_BP/samples/Mono1_H3K27ac/S001YW_NCMLS/problems/chr11:60000-580000/coverage.bedGraph")
  expect_identical(n.lines, 6921L)
})

test_that("wc2int works without initial space", {
  n.lines <- wc2int("6921 /var/folders/7j/bq7gdv517tv9bb54j2tfnt3w0000gn/T//Rtmpu71VKi/file363125abb95f/H3K27ac-H3K4me3_TDHAM_BP/samples/Mono1_H3K27ac/S001YW_NCMLS/problems/chr11:60000-580000/coverage.bedGraph")
  expect_identical(n.lines, 6921L)
})

test_that("wc2int error for bad input", {
  expect_error({
    wc2int(NA_character_)
  }, "input must be non-missing character scalar")
  expect_error({
    wc2int(character())
  }, "input must be non-missing character scalar")
  expect_error({
    wc2int(c("foo", "bar"))
  }, "input must be non-missing character scalar")
  expect_error({
    wc2int(NULL)
  }, "input must be non-missing character scalar")
})

test_that("wc2int error for no size", {
  subj <- "/var/folders/7j/bq7gdv517tv9bb54j2tfnt3w0000gn/T//Rtmpu71VKi/file363125abb95f/H3K27ac-H3K4me3_TDHAM_BP/samples/Mono1_H3K27ac/S001YW_NCMLS/problems/chr11:60000-580000/coverage.bedGraph"
  expect_error({
    wc2int(subj)
  }, error="could not extract line count")
})

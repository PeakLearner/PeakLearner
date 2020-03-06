library(testthat)
library(data.table)
library(PeakSegDisk)
context("CRAN bad paths")

bad.dir <- file.path(tempdir(), "prob (bad)")
dir.create(bad.dir)
foo.csv <- file.path(bad.dir, "foo.csv")
cat("foo bar\n1 2", file=foo.csv)
expected <- data.table(foo=1, bar=2)
test_that("fread.first works with bad path", {
  computed <- fread.first(foo.csv)
  expect_equal(computed, expected)
})
test_that("fread.last works with bad path", {
  computed <- fread.last(foo.csv)
  expect_equal(computed, expected)
})

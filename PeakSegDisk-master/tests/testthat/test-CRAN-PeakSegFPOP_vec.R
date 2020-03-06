library(testthat)
context("PeakSegFPOP_vec")
library(PeakSegDisk)

z.rep.vec <- as.integer(c(1, 3, 0, 4, 2))

test_that("PeakSegFPOP_vec returns 1 segment for pen=Inf", {
  fitInf <- PeakSegDisk::PeakSegFPOP_vec(z.rep.vec, Inf)
  expect_equal(nrow(fitInf$segments), 1)
})

test_that("PeakSegFPOP_vec returns 5 segments for pen=0", {
  fit0 <- PeakSegDisk::PeakSegFPOP_vec(z.rep.vec, 0)
  expect_equal(nrow(fit0$segments), 5)
})


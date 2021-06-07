import PeakSegDiskInterface
import os


def FPOP_files(coverage, segments, loss, penalty, db=None):
    if db is None:
        db = '%s_penalty=%s.db' % (coverage, penalty)
    result = PeakSegDiskInterface.interface(coverage, segments, loss, penalty, db)
    os.remove(db)
    return result



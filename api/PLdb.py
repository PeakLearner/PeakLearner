import os
import api.PLConfig as cfg
import simpleBDB as db


dbPath = os.path.join(cfg.httpServerPath, cfg.dataPath, 'db')

db.createEnvWithDir(dbPath)


def close():
    db.close_db()


class Model(db.Resource):
    keys = ("user", "hub", "track", "chrom", "problemstart", "penalty")
    pass


class Labels(db.Resource):
    keys = ("user", "hub", "track", "chrom", "problemstart")
    pass


class BestModel(db.Resource):
    keys = ("user", "hub", "track", "chrom", "problemstart")
    pass



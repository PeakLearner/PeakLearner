import os
import api.PLConfig as cfg
import simpleBDB as db


dbPath = os.path.join(cfg.httpServerPath, cfg.dataPath, 'db')

db.createEnvWithDir(dbPath)


class Model(db.Resource):
    keys = ("User", "Hub", "Track", "Chrom", "ProblemStart", "Penalty")
    pass


class Labels(db.Resource):
    keys = ("User", "Hub", "Track", "Chrom", "ProblemStart")
    pass


class BestModel(db.Resource):
    keys = ("User", "Hub", "Track", "Chrom", "problemStart")
    pass



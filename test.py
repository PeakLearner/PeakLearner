# needed for any cluster connection
from couchbase.cluster import Cluster, ClusterOptions
from couchbase.auth import PasswordAuthenticator

# needed to support SQL++ (N1QL) query
from couchbase.cluster import QueryOptions

# get a reference to our cluster
from couchbase_core._libcouchbase import Bucket, LOCKMODE_WAIT


def get_bucket(bucket_name):
  cluster = Cluster('couchbase://134.114.109.192', ClusterOptions(
    PasswordAuthenticator('Administrator', 'plcluster')))
  bucket: Bucket = cluster.bucket(bucket_name)
  bucket.timeout = 30
  bucket.n1ql_timeout = 300
  return bucket


from core.util import PLdb as db
db.openDBs()


dbs = {"DoneJob": db.DoneJob,
       'Features': db.Features,
       'HubInfo': db.HubInfo,
       'Iteration': db.Iteration,
       'Job': db.Job,
       'JobInfo': db.JobInfo,
       'Labels': db.Labels,
       'Loss': db.Loss,
       'Model': db.Model,
       'ModelSummaries': db.ModelSummaries,
       'NoPrediction': db.NoPrediction,
       'Permission': db.Permission,
       'Prediction': db.Prediction,
       'Problems': db.Problems}

for key in dbs.keys():
  bucket = get_bucket(key)

  print('bucket got')

  currentDb = dbs[key]

  allVals = currentDb.all()

  print(allVals)



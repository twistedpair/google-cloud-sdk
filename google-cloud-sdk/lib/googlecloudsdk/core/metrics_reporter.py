# Copyright 2015 Google Inc. All Rights Reserved.

"""Script for reporting gcloud metrics."""

import os
import pickle
import sys

import httplib2


# If outgoing packets are getting dropped, httplib2 will hang forever waiting
# for a response.
TIMEOUT_IN_SEC = 10


def ReportMetrics(metrics_file_path):
  """Sends the specified anonymous usage event to the given analytics endpoint.

  Args:
      metrics_file_path: str, File with pickled metrics (list of tuples).
  """
  with open(metrics_file_path, 'rb') as metrics_file:
    metrics = pickle.load(metrics_file)
  os.remove(metrics_file_path)

  http = httplib2.Http(timeout=TIMEOUT_IN_SEC)
  for metric in metrics:
    headers = {'user-agent': metric[3]}
    http.request(metric[0], method=metric[1], body=metric[2], headers=headers)

if __name__ == '__main__':
  try:
    ReportMetrics(sys.argv[1])
  # pylint: disable=bare-except, Never fail or output a stacktrace here.
  except:
    pass

# Copyright 2015 Google Inc. All Rights Reserved.

"""The command group for submitting cloud dataproc jobs."""

import argparse

from googlecloudsdk.calliope import base
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class Submit(base.Group):
  """Submit Google Cloud Dataproc jobs to execute on a cluster."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To submit a Hadoop MapReduce job, run:

            $ {command} hadoop --cluster my_cluster --jar my_jar.jar arg1 arg2

          To submit a Spark Scala or Java job, run:

            $ {command} spark --cluster my_cluster --jar my_jar.jar arg1 arg2

          To submit a PySpark job, run:

            $ {command} pyspark --cluster my_cluster my_script.py arg1 arg2

          To submit a Spark SQL job, run:

            $ {command} spark-sql --cluster my_cluster --file my_queries.q

          To submit a Pig job, run:

            $ {command} pig --cluster my_cluster --file my_script.pig

          To submit a Hive job, run:

            $ {command} hive --cluster my_cluster --file my_queries.q
          """,
  }

  @staticmethod
  def Args(parser):
    # Allow user specified Job ID, but don't expose it.
    parser.add_argument('--id', help=argparse.SUPPRESS)

    parser.add_argument(
        '--async',
        action='store_true',
        help='Does not wait for the job to run.')

    parser.add_argument(
        '--bucket',
        help=("The Cloud Storage bucket to stage files in. Default's to the "
              "cluster's configured bucket"))

# Copyright 2015 Google Inc. All Rights Reserved.

"""Submit a PySpark job to a cluster."""

import argparse

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.third_party.apitools.base import py as apitools_base

from googlecloudsdk.dataproc.lib import base_classes


class PySpark(base_classes.JobSubmitter):
  """Submit a PySpark job to a cluster."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To submit a PySpark job with a local script, run:

            $ {command} --cluster my_cluster my_script.py

          To submit a Spark job that runs a script that is already on the \
cluster, run:

            $ {command} --cluster my_cluster \
file:///usr/lib/spark/examples/src/main/python/pi.py 100
          """,
  }

  @staticmethod
  def Args(parser):
    super(PySpark, PySpark).Args(parser)
    parser.add_argument(
        'py_file',
        help='The main .py file to run as the driver.')
    parser.add_argument(
        '--py-files',
        type=arg_parsers.ArgList(),
        metavar='PY_FILE',
        default=[],
        help=('Comma separated list of Python files to be provided to the job.'
              'Must be one of the following file formats" .py, ,.zip, or .egg'))
    parser.add_argument(
        '--files',
        type=arg_parsers.ArgList(),
        metavar='FILE',
        default=[],
        help='Comma separated list of files to be provided to the job.')
    parser.add_argument(
        '--archives',
        type=arg_parsers.ArgList(),
        metavar='ARCHIVE',
        default=[],
        help=('Comma separated list of archives to be provided to the job. '
              'must be one of the following file formats: .zip, .tar, .tar.gz, '
              'or .tgz.'))
    parser.add_argument(
        'job_args',
        nargs=argparse.REMAINDER,
        help='The arguments to pass to the driver.')
    parser.add_argument(
        '--properties',
        type=arg_parsers.ArgDict(),
        metavar='PROPERTY=VALUE',
        help='A list of key value pairs to configure PySpark.')
    parser.add_argument(
        '--driver-log-levels',
        type=arg_parsers.ArgDict(),
        metavar='PACKAGE=LEVEL',
        help=('A list of package to log4j log level pairs to configure driver '
              'logging. For example: root=FATAL,com.example=INFO'))

  def PopulateFilesByType(self, args, files_by_type):
    # TODO(user): Move arg manipulation elsewhere.
    files_by_type.update({
        'py_file': args.py_file,
        'py_files': args.py_files,
        'archives': args.archives,
        'files': args.files})

  def ConfigureJob(self, job, args, files_by_type):
    messages = self.context['dataproc_messages']

    log_config = self.BuildLoggingConfiguration(args.driver_log_levels)
    pyspark_job = messages.PySparkJob(
        args=args.job_args,
        archiveUris=files_by_type['archives'],
        fileUris=files_by_type['files'],
        pythonFileUris=files_by_type['py_files'],
        mainPythonFileUri=files_by_type['py_file'],
        loggingConfiguration=log_config)

    if args.properties:
      pyspark_job.properties = apitools_base.DictToMessage(
          args.properties, messages.PySparkJob.PropertiesValue)

    job.pysparkJob = pyspark_job

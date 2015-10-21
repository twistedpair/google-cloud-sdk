# Copyright 2015 Google Inc. All Rights Reserved.

"""Submit a Spark job to a cluster."""

import argparse

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.core import log
from googlecloudsdk.third_party.apitools.base import py as apitools_base

from googlecloudsdk.dataproc.lib import base_classes


class Spark(base_classes.JobSubmitter):
  """Submit a Java or Scala Spark job to a cluster."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To submit a Spark job that runs the main class of a jar, run:

            $ {command} --cluster my_cluster --jar my_jar.jar arg1 arg2

          To submit a Spark job that runs a specific class of a jar, run:

            $ {command} --cluster my_cluster --class org.my.main.Class \
--jars my_jar1.jar,my_jar2.jar arg1 arg2

          To submit a Spark job that runs a jar that is already on the \
cluster, run:

            $ {command} --cluster my_cluster \
--class org.apache.spark.examples.SparkPi \
--jars file:///usr/lib/spark/lib/spark-examples.jar 1000
          """,
  }

  @staticmethod
  def Args(parser):
    super(Spark, Spark).Args(parser)
    parser.add_argument(
        '--jar',
        dest='main_jar',
        help='The HCFS URI of jar file containing the driver jar.')
    parser.add_argument(
        '--class',
        dest='main_class',
        help=('The class containing the main method of the driver. Must be in a'
              ' provided jar or jar that is already on the classpath'))
    parser.add_argument(
        '--jars',
        type=arg_parsers.ArgList(),
        metavar='JAR',
        default=[],
        help=('Comma separated list of jar files to be provided to the '
              'Executor and driver classpaths.'))
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
        help='A list of key value pairs to configure Spark.')
    parser.add_argument(
        '--driver-log-levels',
        type=arg_parsers.ArgDict(),
        metavar='PACKAGE=LEVEL',
        help=('A list of package to log4j log level pairs to configure driver '
              'logging. For example: root=FATAL,com.example=INFO'))

  def PopulateFilesByType(self, args, files_by_type):
    # TODO(user): Move arg manipulation elsewhere.
    if not args.main_class and not args.main_jar:
      raise ValueError('Must either specify --class or JAR.')
    if args.main_class and args.main_jar:
      log.info(
          'Both main jar and class specified. Passing main jar as an additional'
          ' jar')
      args.jars.append(args.main_jar)
      args.main_jar = None

    files_by_type.update({
        'main_jar': args.main_jar,
        'jars': args.jars,
        'archives': args.archives,
        'files': args.files})

  def ConfigureJob(self, job, args, files_by_type):
    messages = self.context['dataproc_messages']

    log_config = self.BuildLoggingConfiguration(args.driver_log_levels)
    spark_job = messages.SparkJob(
        args=args.job_args,
        archiveUris=files_by_type['archives'],
        fileUris=files_by_type['files'],
        jarFileUris=files_by_type['jars'],
        mainClass=args.main_class,
        mainJarFileUri=files_by_type['main_jar'],
        loggingConfiguration=log_config)

    if args.properties:
      spark_job.properties = apitools_base.DictToMessage(
          args.properties, messages.SparkJob.PropertiesValue)

    job.sparkJob = spark_job

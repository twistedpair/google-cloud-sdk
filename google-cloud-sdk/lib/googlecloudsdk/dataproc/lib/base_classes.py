# Copyright 2015 Google Inc. All Rights Reserved.

"""Base command classes for shared logic between gcloud dataproc commands."""

# TODO(user): Add more classes.

import abc
import urlparse

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.third_party.apitools.base import py as apitools_base

from googlecloudsdk.dataproc.lib import constants
from googlecloudsdk.dataproc.lib import storage_helpers
from googlecloudsdk.dataproc.lib import util


class JobSubmitter(base.Command):
  """Submit a job to a cluster."""

  __metaclass__ = abc.ABCMeta

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        '--cluster',
        required=True,
        help='The Dataproc cluster to submit the job to.')

  def Run(self, args):
    """This is what gets called when the user runs this command."""
    client = self.context['dataproc_client']
    messages = self.context['dataproc_messages']

    job_id = util.GetJobId(args.id)
    job_ref = util.ParseJob(job_id, self.context)

    files_by_type = {}
    self.PopulateFilesByType(args, files_by_type)

    cluster_ref = util.ParseCluster(args.cluster, self.context)
    request = cluster_ref.Request()

    try:
      cluster = client.projects_clusters.Get(request)
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(util.FormatHttpError(error))

    self.ValidateAndStageFiles(
        bucket=args.bucket,
        cluster=cluster,
        files_by_type=files_by_type)

    job = messages.Job(
        reference=messages.JobReference(
            projectId=job_ref.projectId,
            jobId=job_ref.jobId),
        placement=messages.JobPlacement(
            clusterName=args.cluster))

    self.ConfigureJob(job, args, files_by_type)

    request = messages.DataprocProjectsJobsSubmitRequest(
        projectId=job.reference.projectId,
        submitJobRequest=messages.SubmitJobRequest(
            job=job))

    try:
      job = client.projects_jobs.Submit(request)
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(util.FormatHttpError(error))

    log.status.Print('Job [{0}] submitted.'.format(job_id))

    if not args.async:
      job = util.WaitForJobTermination(
          job,
          self.context,
          message='Waiting for job completion',
          goal_state=messages.JobStatus.StateValueValuesEnum.DONE,
          stream_driver_log=True)
      log.status.Print('Job [{0}] finished successfully.'.format(job_id))

    return job

  def Display(self, args, result):
    self.format(result)

  def ValidateAndStageFiles(self, bucket, cluster, files_by_type):
    """Validate URIs and upload them if they are local."""
    # TODO(user): Clean up / split up functionality.
    files_to_stage = []

    # Lazily determine staging directory since it might require an API call.
    staging_dir = None

    for file_type, files in files_by_type.iteritems():
      singleton = False
      staged_files = []
      if not files:
        continue
      # TODO(user): Remove terrible hack.
      elif isinstance(files, str):
        singleton = True
        files = [files]
      for file_str in files:
        uri = urlparse.urlsplit(file_str, allow_fragments=False)
        if not uri.path:
          raise ValueError(
              '{0} URI [{1}] missing path.'.format(file_type, file_str))
        # TODO(user): Validate file suffixes.
        if uri.scheme:
          # TODO(user): Validate scheme.
          staged_files.append(file_str)
        else:
          if not staging_dir:
            staging_dir = self.GetStagingDir(bucket, cluster)
          basename = uri.path.split('/')[-1]
          staged_file = urlparse.urljoin(staging_dir, basename)
          files_to_stage.append(file_str)
          staged_files.append(staged_file)
      if singleton:
        staged_files = staged_files[0]
      files_by_type[file_type] = staged_files

    if files_to_stage:
      log.info(
          'Staging local files {0} to {1}.'.format(files_to_stage, staging_dir))
      storage_helpers.Upload(files_to_stage, staging_dir)

  def GetStagingDir(self, bucket, cluster):
    """Determine the GCS directory to stage job resources in."""
    if not bucket:
      # Get bucket from cluster.
      bucket = cluster.configuration.configurationBucket
    # TODO(user) Add flag for staging directory.
    staging_dir = 'gs://{0}/{1}/{2}/'.format(
        bucket, constants.GCS_STAGING_PREFIX, cluster.clusterUuid)
    return staging_dir

  def BuildLoggingConfiguration(self, driver_logging):
    """Build LoggingConfiguration from parameters."""
    if not driver_logging:
      return None

    messages = self.context['dataproc_messages']

    return messages.LoggingConfiguration(
        driverLogLevels=apitools_base.DictToMessage(
            driver_logging,
            messages.LoggingConfiguration.DriverLogLevelsValue))

  @abc.abstractmethod
  def ConfigureJob(self, job, args, files_by_type):
    """Add type-specific job configuration to job message."""
    pass

  @abc.abstractmethod
  def PopulateFilesByType(self, args, files_by_type):
    """Take files out of args to allow for them to be staged."""
    pass

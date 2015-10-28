# Copyright 2015 Google Inc. All Rights Reserved.

"""Facility for displaying information about a Job message to a user.
"""

import datetime

from googlecloudsdk.api_lib.bigquery import bigquery_client_helper


class DisplayInfo(object):
  """Information about a job displayed in command output.

  Fields:
     job_id: the job ID
     job_type: one of 'copy', 'extract', 'link', 'load', 'query'
     state: one of 'SUCCESS', 'FAILURE', 'RUNNING'
     start_time: in the form yyyy-mm-dd hh:mm:ss
     duration: in the form h:mm:ss
     bytes_processed (optional)
  """

  def __init__(self, job):
    self.job_id = job.jobReference.jobId
    self.job_type = (
        job.configuration
        and DisplayInfo._JobTypeForConfiguration(job.configuration))
    if job.status.state == 'DONE':
      self.state = 'FAILURE' if job.status.errorResult else 'SUCCESS'
    else:
      self.state = job.status.state
    if job.statistics.startTime:
      start_time_in_seconds = int(job.statistics.startTime / 1000)
      self.start_time = bigquery_client_helper.FormatTime(
          job.statistics.startTime)
      if job.statistics.endTime:
        end_time_in_seconds = int(job.statistics.endTime / 1000)
        duration_seconds = end_time_in_seconds - start_time_in_seconds
        self.duration = str(datetime.timedelta(seconds=duration_seconds))
    self.bytes_processed = job.statistics.totalBytesProcessed

  @staticmethod
  def _JobTypeForConfiguration(configuration):
    """Determines the type of job corresponding to a JobConfiguration message.

    Args:
      configuration: The JobConfiguration message.

    Returns:
      One of the strings 'copy', 'extract', 'load', or 'query'.
    """
    if configuration.copy:
      return 'copy'
    if configuration.extract:
      return 'extract'
    if configuration.link:
      return 'link'
    if configuration.load:
      return 'load'
    if configuration.query:
      return 'query'
    return None

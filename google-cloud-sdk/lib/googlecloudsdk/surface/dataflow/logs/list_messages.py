# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud dataflow logs list-messages command.
"""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.shared.dataflow import job_utils
from googlecloudsdk.shared.dataflow import list_pager
from googlecloudsdk.shared.dataflow import time_util
from googlecloudsdk.surface import dataflow as commands


class ListMessages(base.Command):
  """Retrieve the logs from a specific job using the GetMessages RPC.

  This is intended for short-term use and will be removed once the CLI based on
  Cloud Logging is available.
  """

  @staticmethod
  def Args(parser):
    job_utils.ArgsForJobRef(parser)

    parser.add_argument(
        '--after', type=time_util.ParseTimeArg,
        help='Only display messages logged after the given time.')
    parser.add_argument(
        '--before', type=time_util.ParseTimeArg,
        help='Only display messages logged before the given time.')
    parser.add_argument(
        '--importance', choices=['debug', 'detailed', 'warning', 'error'],
        help='Minimum importance a message must have to be displayed',
        default='warning')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: all the arguments that were provided to this command invocation.

    Returns:
      None on success, or a string containing the error message.
    """
    apitools_client = self.context[commands.DATAFLOW_APITOOLS_CLIENT_KEY]
    dataflow_messages = self.context[commands.DATAFLOW_MESSAGES_MODULE_KEY]
    job_ref = job_utils.ExtractJobRef(self.context, args)

    importance_enum = (
        dataflow_messages.DataflowProjectsJobsMessagesListRequest
        .MinimumImportanceValueValuesEnum)
    importance_map = {
        'debug': importance_enum.JOB_MESSAGE_DEBUG,
        'detailed': importance_enum.JOB_MESSAGE_DETAILED,
        'error': importance_enum.JOB_MESSAGE_ERROR,
        'warning': importance_enum.JOB_MESSAGE_WARNING,
    }

    request = dataflow_messages.DataflowProjectsJobsMessagesListRequest(
        projectId=job_ref.projectId,
        jobId=job_ref.jobId,
        minimumImportance=(args.importance and importance_map[args.importance]),

        # Note: It if both are present, startTime > endTime, because we will
        # return messages with actual time [endTime, startTime).
        startTime=args.before and time_util.Strftime(args.before),
        endTime=args.after and time_util.Strftime(args.after))

    return self._GetMessages(apitools_client, request)

  def _GetMessages(self, apitools_client, request):
    return list_pager.YieldFromList(
        apitools_client.projects_jobs_messages,
        request,
        batch_size=None,  # Use server default.
        field='jobMessages')

  def Display(self, args, logs):
    """This method is called to print the result of the Run() method.

    Args:
      args: all the arguments that were provided to this command invocation.
      logs: The logs returned from the Run() method.
    """
    if not args.format or args.format == 'text':
      importance_enum = (
          self.context[commands.DATAFLOW_MESSAGES_MODULE_KEY].JobMessage.
          MessageImportanceValueValuesEnum)
      importances = {
          importance_enum.JOB_MESSAGE_DETAILED: 'd',
          importance_enum.JOB_MESSAGE_DEBUG: 'D',
          importance_enum.JOB_MESSAGE_WARNING: 'W',
          importance_enum.JOB_MESSAGE_ERROR: 'E',
      }
      for msg in logs:
        log.out.Print('{0} {1} {2} {3}'.format(
            importances.get(msg.messageImportance, '?'),
            time_util.FormatTimestamp(msg.time),
            msg.id,
            msg.messageText))
    else:
      self.format(logs)

# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud dataflow jobs list command.
"""

from googlecloudsdk.api_lib.dataflow import job_display
from googlecloudsdk.api_lib.dataflow import job_utils
from googlecloudsdk.api_lib.dataflow import list_pager
from googlecloudsdk.api_lib.dataflow import time_util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import properties
from googlecloudsdk.surface import dataflow as commands


class List(base.Command):
  """Lists all jobs in a particular project.

  By default, jobs in the current project are listed; this can be overridden
  with the gcloud --project flag.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    # Flags for specifying job refs directly
    job_utils.ArgsForJobRefs(parser, nargs='*')

    # Flags for filtering jobs.
    parser.add_argument('--job-name',
                        help='Filter the jobs to those with the given name.')
    parser.add_argument(
        '--status', action='append',
        choices=['running', 'stopped', 'done', 'cancelled', 'failed',
                 'updated'],
        help='Filter the jobs to those with the selected status')
    parser.add_argument(
        '--created-after', type=time_util.ParseTimeArg,
        help='Filter the jobs to those created after the given time')
    parser.add_argument(
        '--created-before', type=time_util.ParseTimeArg,
        help='Filter the jobs to those created before the given time')

  def Run(self, args):
    """Runs the command.

    Args:
      args: All the arguments that were provided to this command invocation.

    Returns:
      An iterator over Job messages.
    """
    job_refs = job_utils.ExtractJobRefs(self.context, args)
    filter_pred = _JobFilter(self.context, args)

    if job_refs and not filter_pred.AlwaysTrue():
      raise calliope_exceptions.ToolException(
          'Cannot specify both job IDs and job filters.')

    jobs = []
    if job_refs:
      view = job_utils.JOB_VIEW_SUMMARY
      jobs = [job_utils.GetJob(self.context, job_ref, view=view)
              for job_ref in job_refs]
    else:
      project_id = properties.VALUES.core.project.Get(required=True)
      jobs = self._JobSummariesForProject(project_id, filter_pred)

    dataflow_messages = self.context[commands.DATAFLOW_MESSAGES_MODULE_KEY]
    return [job_display.DisplayInfo(job, dataflow_messages) for job in jobs]

  def Display(self, args, jobs):
    """This method is called to print the result of the Run() method.

    Args:
      args: all the arguments that were provided to this command invocation.
      jobs: The iterator over Job messages returned from the Run() method.
    """
    list_printer.PrintResourceList('dataflow.jobs', jobs)

  def _JobSummariesForProject(self, project_id, filter_predicate):
    """Get the list of job summaries that match the predicate.

    Args:
      project_id: The project ID to retrieve
      filter_predicate: The filter predicate to apply

    Returns:
      An iterator over all the matching jobs.
    """
    apitools_client = self.context[commands.DATAFLOW_APITOOLS_CLIENT_KEY]
    req_class = (self.context[commands.DATAFLOW_MESSAGES_MODULE_KEY]
                 .DataflowProjectsJobsListRequest)
    request = req_class(
        projectId=project_id,
        view=job_utils.JOB_VIEW_SUMMARY.JobsListRequest(self.context))
    return list_pager.YieldFromList(
        apitools_client.projects_jobs,
        request,
        batch_size=None,  # Use server default.
        field='jobs',
        predicate=filter_predicate)


class _JobFilter(object):
  """Predicate for filtering jobs.
  """

  def __init__(self, context, args):
    """Create a _JobFilter from the given args.

    Args:
      context: The command context.
      args: The argparse.Namespace containing the parsed arguments.
    """
    self.preds = []
    if args.status:
      self._ParseStatusSet(context, args.status)

    if args.created_after or args.created_before:
      self._ParseTimePredicate(args.created_after, args.created_before)

    if args.job_name:
      self.preds.append(lambda x: x.name and args.job_name in x.name)

  def __call__(self, job):
    return all([pred(job) for pred in self.preds])

  def AlwaysTrue(self):
    return not self.preds

  def _ParseStatusSet(self, context, status_list):
    """Parse a list of status enums from a list of command line flags.

    Args:
      context: The command context.
      status_list: A list containing status strings, such as 'cancelled',
          'done', 'failed', etc.
    Returns:
      A list containing enums from Job.CurrentStateValueValuesEnum.
    """
    state_value_enum = (context[commands.DATAFLOW_MESSAGES_MODULE_KEY]
                        .Job.CurrentStateValueValuesEnum)
    message_map = {
        'cancelled': state_value_enum.JOB_STATE_CANCELLED,
        'done': state_value_enum.JOB_STATE_DONE,
        'failed': state_value_enum.JOB_STATE_FAILED,
        'running': state_value_enum.JOB_STATE_RUNNING,
        'stopped': state_value_enum.JOB_STATE_STOPPED,
        'updated': state_value_enum.JOB_STATE_UPDATED,
        'unknown': state_value_enum.JOB_STATE_UNKNOWN,
    }

    status_set = frozenset([message_map[status] for status in status_list])
    self.preds.append(lambda x: x.currentState in status_set)

  def _ParseTimePredicate(self, after, before):
    """Return a predicate for filtering jobs by their creation time.

    Args:
      after: Only return true if the job was created after this time.
      before: Only return true if the job was created before this time.

    """
    if after and (not before):
      self.preds.append(lambda x: time_util.Strptime(x.createTime) > after)
    elif (not after) and before:
      self.preds.append(lambda x: time_util.Strptime(x.createTime) <= before)
    elif after and before:
      def _Predicate(x):
        create_time = time_util.Strptime(x.createTime)
        return after < create_time and create_time <= before
      self.preds.append(_Predicate)

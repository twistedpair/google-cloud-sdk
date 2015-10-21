# Copyright 2015 Google Inc. All Rights Reserved.

"""List job command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apitools.base import py as apitools_base

from googlecloudsdk.dataproc.lib import util


STATE_MATCHER_ENUM = ['active', 'inactive']


class TypedJob(util.Bunch):
  """Job with additional type field that corresponds to the job_type one_of."""

  def __init__(self, job):
    super(TypedJob, self).__init__(apitools_base.MessageToDict(job))
    self._job = job
    self._type = None

  @property
  def type(self):
    for field in [field.name for field in self._job.all_fields()]:
      if field.endswith('Job'):
        job_type, _, _ = field.rpartition('Job')
        if self._job.get_assigned_value(field):
          return job_type
    raise AttributeError('Job has no job type')


class List(base.Command):
  """List all jobs in a project."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To see the list of all jobs, run:

            $ {command}

          To see the list of all active jobs in a cluster, run:

            $ {command} --state-filter active --cluster my_cluster
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--cluster',
        help='Restrict to the jobs of this Dataproc cluster.')

    parser.add_argument(
        '--state-filter',
        choices=STATE_MATCHER_ENUM,
        help='Filter by job state. Choices are {0}.'.format(STATE_MATCHER_ENUM))

  @util.HandleHttpError
  def Run(self, args):
    client = self.context['dataproc_client']
    messages = self.context['dataproc_messages']

    project = properties.VALUES.core.project.Get(required=True)
    request = messages.DataprocProjectsJobsListRequest(projectId=project)

    if args.cluster:
      request.clusterName = args.cluster

    if args.state_filter:
      if args.state_filter == 'active':
        request.jobStateMatcher = (
            messages.DataprocProjectsJobsListRequest.JobStateMatcher.ACTIVE)
      elif args.state_filter == 'inactive':
        request.jobStateMatcher = (
            messages.DataprocProjectsJobsListRequest.JobStateMatcher.NON_ACTIVE)
      else:
        raise exceptions.ToolException(
            'Invalid state-filter; [{0}].'.format(args.state_filter))

    response = client.projects_jobs.List(request)
    return response.jobs

  def Display(self, args, result):
    result = [TypedJob(job) for job in result]
    list_printer.PrintResourceList('dataproc.jobs', result)

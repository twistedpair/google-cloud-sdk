# Copyright 2014 Google Inc. All Rights Reserved.

"""replicapool list command."""

from apiclient import errors
from googlecloudsdk.api_lib.compute import rolling_updates_util as util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


class List(base.Command):
  """List all replica pools in a given project."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument('--limit', type=int,
                        help='The maximum number of results to list.')
    l = parser.add_argument(
        '-l', '--human-readable',
        action='store_true',
        help='If provided, a human-readable table of useful data is printed.')
    l.detailed_help = """\
        If provided, prints a human-readable table of replica pool names and
        currentNumReplicas for each replica pool. The table output is for
        convenience and should not be scripted against as it could
        change without notice.
        """

  def Run(self, args):
    """Run 'replicapool list'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      An object representing the service response obtained by the List
      API if the List call was successful.

    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing
          the command.
    """
    client = self.context['replicapool']
    project = properties.VALUES.core.project.Get(required=True)

    limit = util.SanitizeLimitFlag(args.limit)

    request = client.pools().list(projectName=project, zone=args.zone)
    results = []
    try:
      response = request.execute()
      self.AppendResults(results, response)
      while response and 'nextPageToken' in response and len(results) < limit:
        request = client.pools().list(projectName=project,
                                      zone=args.zone,
                                      pageToken=response['nextPageToken'])
        response = request.execute()
        self.AppendResults(results, response)

      if len(results) > limit:
        results = results[0:limit]

      return results
    except errors.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))
    except errors.Error as error:
      raise exceptions.ToolException(error)

  def AppendResults(self, results, response):
    # TODO(sepehr): refactor this to a common library when we move to apitools
    if results is None or response is None:
      raise ValueError('Unexpected input! ' + results + ' ' + response)

    if response and 'resources' in response:
      results.extend(response['resources'])

  def Display(self, args, result):
    """Display prints information about what just happened to stdout.

    Args:
      args: The same as the args in Run.
      result: a list of dicts, where each dict has information about one
          replica pool
    """
    if not result:
      log.Print('No replica pools were found!')
      return

    if args.human_readable:
      util.PrintTable(result, 'replica-pool')
    else:
      for replicapool in result:
        log.Print(replicapool['selfLink'])

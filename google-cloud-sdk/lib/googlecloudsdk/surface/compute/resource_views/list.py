# Copyright 2014 Google Inc. All Rights Reserved.

"""resourceviews list command."""

from apiclient import errors
from googlecloudsdk.api_lib.compute import rolling_updates_util as util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


class List(base.Command):
  """List all resource views for a given project."""

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

  def Run(self, args):
    """Run 'resourceviews list'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A list object representing the resource views obtained by the List
      operation if the List API call was successful.

    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing
          the command.
    """
    limit = util.SanitizeLimitFlag(args.limit)

    request = self.BuildRequest(args)
    results = []
    try:
      response = request.execute()
      self.AppendResults(results, response)
      while response and 'nextPageToken' in response and len(results) < limit:
        request = self.BuildRequest(args, response['nextPageToken'])
        response = request.execute()
        self.AppendResults(results, response)

      if len(results) > limit:
        results = results[0:limit]

      return results
    except errors.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))
    except errors.Error as error:
      raise exceptions.ToolException(error)

  def BuildRequest(self, args, page_token=None):
    zone_views_client = self.context['zoneViewsClient']
    region_views_client = self.context['regionViewsClient']

    project = properties.VALUES.core.project.Get(required=True)
    if 'v1beta1' in self.context['api_version']:
      if args.region:
        return region_views_client.list(
            projectName=project,
            region=args.region,
            pageToken=page_token)
      else:
        return zone_views_client.list(
            projectName=project,
            zone=args.zone,
            pageToken=page_token)
    else:
      return zone_views_client.list(
          project=project,
          zone=args.zone,
          pageToken=page_token)

  def AppendResults(self, results, response):
    # TODO(sepehr): refactor this to a common library when we move to apitools
    if results is None or response is None:
      raise ValueError('Unexpected input! ' + results + ' ' + response)

    # TODO(sepehr): Remove the first if-statement when v1beta1 is deprecated
    if response and 'resourceViews' in response:
      results.extend(response['resourceViews'])
    elif response and 'items' in response:
      results.extend(response['items'])

  def Display(self, unused_args, results):
    """Display prints information about what just happened to stdout.

    Args:
      unused_args: The same as the args in Run.
      results: The results of the Run() method.
    """
    for resource_view in results:
      log.Print(resource_view['selfLink'])

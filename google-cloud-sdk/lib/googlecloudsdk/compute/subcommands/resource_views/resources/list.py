# Copyright 2014 Google Inc. All Rights Reserved.

"""'resourceviews resources list' command."""


from apiclient import errors
from googlecloudsdk.api_lib.compute import rolling_updates_util as util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


class List(base.Command):
  """List resources in a resource view."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument('--limit',
                        type=int,
                        help='The maximum number of results to list.')

    parser.add_argument(
        '-l', '--human-readable',
        action='store_true',
        help='If provided, a list of instance name is printed.')

  def Run(self, args):
    """Run 'resourceviews resources list'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A list object representing the resources in a view obtained by the
      ListResources operation if the ListResources API call was successful.

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
        return region_views_client.listresources(
            projectName=project,
            region=args.region,
            resourceViewName=args.resourceview,
            pageToken=page_token)
      else:
        return zone_views_client.listresources(
            projectName=project,
            zone=args.zone,
            resourceViewName=args.resourceview,
            pageToken=page_token)
    else:
      return zone_views_client.listResources(
          project=project,
          zone=args.zone,
          resourceView=args.resourceview,
          pageToken=page_token)

  def AppendResults(self, results, response):
    # TODO(user): refactor this to a common library when we move to apitools
    if results is None or response is None:
      raise ValueError('Unexpected input! ' + results + ' ' + response)

    if response and 'members' in response:
      results.extend(response['members'])
    elif response and 'items' in response:
      # TODO(user): Change this to print the actual response for v1beta2 only
      for item in response['items']:
        results.append(item['resource'])

  def Display(self, args, results):
    """Display prints information about what just happened to stdout.

    Args:
      args: The same as the args in Run.
      results: The results of the Run() method.
    """
    for resource in results:
      if args.limit:
        log.Print(self.GetInstanceNameFromUrl(resource))
      else:
        log.Print(resource)

  def GetInstanceNameFromUrl(self, url):
    """Extract the instance name from the instance URL.

    Args:
      url: the instance url.

    Returns:
      The instance name.
    """

    last_slash = url.rfind('/')
    return url[last_slash + 1:]

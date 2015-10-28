# Copyright 2015 Google Inc. All Rights Reserved.
"""Cloud Pub/Sub subscription list command."""
import re
from googlecloudsdk.api_lib.pubsub import util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as sdk_ex
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io as io

MAX_SUBSCRIPTIONS_RESULTS = 5000


class List(base.Command):
  """Lists Cloud Pub/Sub subscriptions.

  Lists all of the Cloud Pub/Sub subscriptions that exist in a given project.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""

    parser.add_argument(
        '--name-filter', default='',
        help=('A regular expression that will limit which subscriptions are'
              ' returned by matching on subscription name.'))
    parser.add_argument(
        '--max-results', type=int, default=500,
        help=('The maximum number of subscriptions that this command may'
              ' return. The upper limit for this argument is {0}'.format(
                  MAX_SUBSCRIPTIONS_RESULTS)))

  @util.MapHttpError
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Yields:
      Subscription paths that match the regular expression in args.name_filter.

    Raises:
      sdk_ex.HttpException if there is an error with the regular
      expression syntax.
    """
    msgs = self.context['pubsub_msgs']
    pubsub = self.context['pubsub']

    try:
      list_subscriptions_response = pubsub.projects_subscriptions.List(
          msgs.PubsubProjectsSubscriptionsListRequest(
              project=util.ProjectFormat(),
              pageSize=min(args.max_results, MAX_SUBSCRIPTIONS_RESULTS)))

      for subscription in list_subscriptions_response.subscriptions:
        if util.SubscriptionMatches(subscription.name, args.name_filter):
          yield subscription

      if list_subscriptions_response.nextPageToken:
        log.err.Print(
            'More subscriptions exist, but the result was truncated.')
    except re.error as e:
      raise sdk_ex.HttpException(str(e))

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    tbl = io.TablePrinter(
        ['SUBSCRIPTION', 'TYPE', 'ACK DEADLINE'],
        justification=tuple(
            [io.TablePrinter.JUSTIFY_LEFT] * 3))

    tbl.Print(
        [TableValues(subscription) for subscription in result])


def TableValues(subscription):
  """Converts a Subscription into a tuple of column values."""

  type_ = 'PULL'
  if subscription.pushConfig.pushEndpoint:
    type_ = 'PUSH'
  return (subscription.name, type_, str(subscription.ackDeadlineSeconds))

# Copyright 2015 Google Inc. All Rights Reserved.
"""Cloud Pub/Sub topics list_subscriptions command."""
import re

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as sdk_ex
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io as io
from googlecloudsdk.shared.pubsub import util

MAX_SUBSCRIPTIONS_RESULTS = 5000


class ListSubscriptions(base.Command):
  """Lists Cloud Pub/Sub subscriptions from a given topic.

  Lists all of the Cloud Pub/Sub subscriptions attached to the given topic and
  that match the given filter.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""

    parser.add_argument(
        'topic',
        help=('The name of the topic to list subscriptions for.'))
    parser.add_argument(
        '--name-filter', '-f', default='',
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
      Subscriptions paths that match the regular expression in args.name_filter.
    """
    msgs = self.context['pubsub_msgs']
    pubsub = self.context['pubsub']

    try:
      list_subscriptions_result = pubsub.projects_topics_subscriptions.List(
          msgs.PubsubProjectsTopicsSubscriptionsListRequest(
              topic=util.TopicFormat(args.topic),
              pageSize=min(args.max_results, MAX_SUBSCRIPTIONS_RESULTS)))

      for subscription in list_subscriptions_result.subscriptions:
        if util.SubscriptionMatches(subscription, args.name_filter):
          yield subscription

      if list_subscriptions_result.nextPageToken:
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
    subscriptions = [subscription for subscription in result]
    printer = io.ListPrinter(
        '{0} subscriptions(s) found'.format(len(subscriptions)))
    printer.Print(subscriptions)

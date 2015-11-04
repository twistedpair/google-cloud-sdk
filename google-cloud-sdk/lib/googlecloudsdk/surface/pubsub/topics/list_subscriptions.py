# Copyright 2015 Google Inc. All Rights Reserved.
"""Cloud Pub/Sub topics list_subscriptions command."""
import re
from googlecloudsdk.api_lib.pubsub import util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as sdk_ex
from googlecloudsdk.core.console import console_io as io


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
        '--max-results', type=int, default=0,
        help=('The maximum number of subscriptions that this'
              ' command may return.'
              'This option is ignored if --name-filter is set.'))

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

    page_token = None
    subscriptions_listed = 0
    should_truncate_res = args.max_results and not args.name_filter

    try:
      while True:
        list_subscriptions_req = (
            msgs.PubsubProjectsTopicsSubscriptionsListRequest(
                topic=util.TopicFormat(args.topic),
                pageToken=page_token))

        if should_truncate_res:
          list_subscriptions_req.pageSize = min(args.max_results,
                                                util.MAX_LIST_RESULTS)

        list_subscriptions_result = pubsub.projects_topics_subscriptions.List(
            list_subscriptions_req)

        for subscription in list_subscriptions_result.subscriptions:
          if not util.SubscriptionMatches(subscription, args.name_filter):
            continue

          # If max_results > 0 and we have already sent that
          # amount of subscriptions, just raise (StopIteration) iff name_filter
          # is not set, else this limit wouldn't make sense.
          if should_truncate_res and subscriptions_listed >= args.max_results:
            raise StopIteration()

          subscriptions_listed += 1
          yield subscription

        page_token = list_subscriptions_result.nextPageToken
        if not page_token:
          break

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

# Copyright 2015 Google Inc. All Rights Reserved.
"""Cloud Pub/Sub topics list command."""
import re
from googlecloudsdk.api_lib.pubsub import util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as sdk_ex
from googlecloudsdk.core.console import console_io as io


class List(base.Command):
  """Lists Cloud Pub/Sub topics within a project.

  Lists all of the Cloud Pub/Sub topics that exist in a given project that
  match the given topic name filter.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""

    parser.add_argument(
        '--name-filter', default='',
        help=('A regular expression that will limit which topics are returned'
              ' by matching on topic name.'))
    parser.add_argument(
        '--max-results', type=int, default=0,
        help=('The maximum number of topics that this command may return.'
              'This option is ignored if --name-filter is set.'))

  @util.MapHttpError
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Yields:
      Topic paths that match the regular expression in args.name_filter.
    """
    msgs = self.context['pubsub_msgs']
    pubsub = self.context['pubsub']

    page_token = None
    topics_listed = 0
    should_truncate_resp = args.max_results and not args.name_filter

    try:
      while True:
        list_topics_request = msgs.PubsubProjectsTopicsListRequest(
            project=util.ProjectFormat(),
            pageToken=page_token)

        if should_truncate_resp:
          list_topics_request.pageSize = min(args.max_results,
                                             util.MAX_LIST_RESULTS)

        list_topics_response = pubsub.projects_topics.List(
            list_topics_request)

        for topic in list_topics_response.topics:
          if not util.TopicMatches(topic.name, args.name_filter):
            continue

          # If max_results > 0 and we have already sent that
          # amount of subscriptions, just raise (StopIteration) iff name_filter
          # is not set, else this limit wouldn't make sense.
          if should_truncate_resp and topics_listed >= args.max_results:
            raise StopIteration()

          topics_listed += 1
          yield topic

        page_token = list_topics_response.nextPageToken
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
    topics = [topic.name for topic in result]
    printer = io.ListPrinter('{0} topic(s) found'.format(len(topics)))
    printer.Print(topics)

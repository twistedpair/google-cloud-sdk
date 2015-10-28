# Copyright 2015 Google Inc. All Rights Reserved.
"""Cloud Pub/Sub topics list command."""
import re
from googlecloudsdk.api_lib.pubsub import util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as sdk_ex
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io as io

MAX_TOPICS_RESULTS = 1000


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
        '--max-results', type=int, default=500,
        help=('The maximum number of topics that this command may return.'
              ' The upper limit for this argument is {0}.'.format(
                  MAX_TOPICS_RESULTS)))

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

    try:
      list_topics_response = pubsub.projects_topics.List(
          msgs.PubsubProjectsTopicsListRequest(
              project=util.ProjectFormat(),
              pageSize=min(args.max_results, MAX_TOPICS_RESULTS)))

      for topic in list_topics_response.topics:
        if util.TopicMatches(topic.name, args.name_filter):
          yield topic

      if list_topics_response.nextPageToken:
        log.err.Print(
            'More topics exist, but the result was truncated.')

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

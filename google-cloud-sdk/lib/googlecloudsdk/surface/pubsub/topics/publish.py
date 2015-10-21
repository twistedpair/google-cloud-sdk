# Copyright 2015 Google Inc. All Rights Reserved.
"""Cloud Pub/Sub topics publish command."""
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as sdk_ex
from googlecloudsdk.core.console import console_io as io
from googlecloudsdk.shared.pubsub import util

MAX_ATTRIBUTES = 100


class Publish(base.Command):
  """Publishes a message to the specified topic.

  Publishes a message to the specified topic name for testing and
  troubleshooting. Use with caution: all associated subscribers must be
  able to consume and acknowledge any message you publish, otherwise the
  system will continuously re-attempt delivery of the bad message for 7 days.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""

    parser.add_argument('topic', help='Topic name to publish messages to.')
    parser.add_argument('message_body', nargs='?', default=None,
                        help=('The body of the message to publish to the'
                              ' given topic name.'))
    parser.add_argument('--attribute',
                        type=arg_parsers.ArgDict(max_length=MAX_ATTRIBUTES),
                        help=('Comma-separated list of attributes.'
                              ' Each ATTRIBUTE has the form "name=value".'
                              ' You can specify up to {0} attributes.'.format(
                                  MAX_ATTRIBUTES)))

  @util.MapHttpError
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      PublishResponse with the response of the Publish operation.

    Raises:
      sdk_ex.HttpException: If attributes are malformed, or if none of
      MESSAGE_BODY or ATTRIBUTE are given.
    """
    msgs = self.context['pubsub_msgs']
    pubsub = self.context['pubsub']

    attributes = []
    if args.attribute:
      for key, value in sorted(args.attribute.iteritems()):
        attributes.append(
            msgs.PubsubMessage.AttributesValue.AdditionalProperty(
                key=key,
                value=value))

    if not args.message_body and not attributes:
      raise sdk_ex.HttpException(('You cannot send an empty message.'
                                  ' You must specify either a MESSAGE_BODY,'
                                  ' one or more ATTRIBUTE, or both.'))

    message = msgs.PubsubMessage(
        data=args.message_body,
        attributes=msgs.PubsubMessage.AttributesValue(
            additionalProperties=attributes))

    return pubsub.projects_topics.Publish(
        msgs.PubsubProjectsTopicsPublishRequest(
            publishRequest=msgs.PublishRequest(messages=[message]),
            topic=util.TopicFormat(args.topic)))

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    printer = io.ListPrinter(
        '{0} message(s) published.'.format(len(result.messageIds)))
    printer.Print(['messageId: {0}'.format(msg) for msg in result.messageIds])

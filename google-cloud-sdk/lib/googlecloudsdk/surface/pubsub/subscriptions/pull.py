# Copyright 2015 Google Inc. All Rights Reserved.
"""Cloud Pub/Sub subscription pull command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core.console import console_io as io
from googlecloudsdk.shared.pubsub import util


class Pull(base.Command):
  """Pulls one or more Cloud Pub/Sub messages from a subscription.

  Returns one or more messages from the specified Cloud Pub/Sub subscription,
  if there are any messages enqueued.
  """

  @staticmethod
  def Args(parser):
    """Registers flags for this command."""

    parser.add_argument('subscription',
                        help='Name of subscription to pull messages from.')
    parser.add_argument(
        '--max-messages', type=int, default=1,
        help=('The maximum number of messages that Cloud Pub/Sub can return'
              ' in this response.'))
    parser.add_argument(
        '--auto-ack', action='store_true', default=False,
        help=('Automatically ACK every message pulled from this subscription.'))

  @util.MapHttpError
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      A PullResponse message with the response of the Pull operation.
    """
    msgs = self.context['pubsub_msgs']
    pubsub = self.context['pubsub']

    pull_req = msgs.PubsubProjectsSubscriptionsPullRequest(
        pullRequest=msgs.PullRequest(
            maxMessages=args.max_messages, returnImmediately=True),
        subscription=util.SubscriptionFormat(args.subscription))

    pull_response = pubsub.projects_subscriptions.Pull(pull_req)

    if args.auto_ack and pull_response.receivedMessages:
      ack_ids = [message.ackId for message in pull_response.receivedMessages]

      ack_req = msgs.PubsubProjectsSubscriptionsAcknowledgeRequest(
          acknowledgeRequest=msgs.AcknowledgeRequest(ackIds=ack_ids),
          subscription=util.SubscriptionFormat(args.subscription))
      pubsub.projects_subscriptions.Acknowledge(ack_req)

    return pull_response

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """

    tbl_header = ['DATA', 'MESSAGE_ID', 'ATTRIBUTES']
    if not args.auto_ack:
      tbl_header.append('ACK_ID')

    tbl = io.TablePrinter(
        tbl_header,
        justification=tuple(
            [io.TablePrinter.JUSTIFY_LEFT] * len(tbl_header)))

    tbl.Print(
        [TableValues(msg, args.auto_ack) for msg in result.receivedMessages])


def TableValues(result, hide_ack=False):
  """Converts a receivedMessage into a tuple of column values."""

  attributes = []
  if result.message.attributes:
    for attr in result.message.attributes.additionalProperties:
      attributes.append('='.join((attr.key, attr.value)))

  return_val = [result.message.data,
                result.message.messageId,
                ' '.join(attributes)]

  if not hide_ack:
    return_val.append(result.ackId)

  return return_val

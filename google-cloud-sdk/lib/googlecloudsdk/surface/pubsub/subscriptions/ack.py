# Copyright 2015 Google Inc. All Rights Reserved.
"""Cloud Pub/Sub topics publish command."""

from googlecloudsdk.api_lib.pubsub import util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log


class Ack(base.Command):
  """Acknowledges one or more messages on the specified subscription.

  Acknowledges one or more messages as having been successfully received.
  If a delivered message is not acknowledged, Cloud Pub/Sub will attempt to
  deliver it again.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""

    parser.add_argument('subscription',
                        help='Subscription name to ACK messages on.')
    parser.add_argument('ackid', nargs='+',
                        help='One or more AckId to acknowledge.')

  @util.MapHttpError
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      None
    """
    msgs = self.context['pubsub_msgs']
    pubsub = self.context['pubsub']

    ack_req = msgs.PubsubProjectsSubscriptionsAcknowledgeRequest(
        acknowledgeRequest=msgs.AcknowledgeRequest(ackIds=args.ackid),
        subscription=util.SubscriptionFormat(args.subscription))

    pubsub.projects_subscriptions.Acknowledge(ack_req)

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    log.out.Print('{0} message(s) acknowledged for subscription {1}'.format(
        len(args.ackid), util.SubscriptionFormat(args.subscription)))

# Copyright 2015 Google Inc. All Rights Reserved.
"""Cloud Pub/Sub subscription modify command."""

from googlecloudsdk.api_lib.pubsub import util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log


class ModifyAckDeadline(base.Command):
  """Modifies the ACK deadline for a specific Cloud Pub/Sub message.

  This method is useful to indicate that more time is needed to process a
  message by the subscriber, or to make the message available for
  redelivery if the processing was interrupted.
  """

  @staticmethod
  def Args(parser):
    """Registers flags for this command."""

    parser.add_argument('subscription',
                        help='Name of the subscription messages belong to.')
    parser.add_argument('ackid', nargs='+',
                        help=('One or more ACK_ID that identify the messages'
                              ' to modify the deadline for.'))
    parser.add_argument(
        '--ack-deadline', type=int, required=True,
        help=('The number of seconds the system will wait for a subscriber to'
              ' acknowledge receiving a message before re-attempting'
              ' delivery.'))

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

    mod_req = msgs.PubsubProjectsSubscriptionsModifyAckDeadlineRequest(
        modifyAckDeadlineRequest=msgs.ModifyAckDeadlineRequest(
            ackDeadlineSeconds=args.ack_deadline,
            ackIds=args.ackid),
        subscription=util.SubscriptionFormat(args.subscription))

    pubsub.projects_subscriptions.ModifyAckDeadline(mod_req)

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    log.out.Print('New ACK deadline: {0} second(s)'.format(args.ack_deadline))

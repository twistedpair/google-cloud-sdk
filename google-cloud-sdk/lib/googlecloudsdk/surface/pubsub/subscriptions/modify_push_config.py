# Copyright 2015 Google Inc. All Rights Reserved.
"""Cloud Pub/Sub subscription modify-push-config command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.shared.pubsub import util


class ModifyPushConfig(base.Command):
  """Modifies the push configuration of a Cloud Pub/Sub subscription."""

  @staticmethod
  def Args(parser):
    """Registers flags for this command."""

    parser.add_argument('subscription',
                        help='Name of the subscription to modify.')
    parser.add_argument(
        '--push-endpoint', required=True,
        help=('A URL to use as the endpoint for this subscription.'
              ' This will also automatically set the subscription'
              ' type to PUSH.'))

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

    mod_req = msgs.PubsubProjectsSubscriptionsModifyPushConfigRequest(
        modifyPushConfigRequest=msgs.ModifyPushConfigRequest(
            pushConfig=msgs.PushConfig(pushEndpoint=args.push_endpoint)),
        subscription=util.SubscriptionFormat(args.subscription))

    pubsub.projects_subscriptions.ModifyPushConfig(mod_req)

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    log.out.Print('New Push Endpoint URL:')
    log.out.Print('"{0}"'.format(args.push_endpoint))

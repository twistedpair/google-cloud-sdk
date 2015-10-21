# Copyright 2015 Google Inc. All Rights Reserved.
"""Cloud Pub/Sub subscription delete command."""

import json

from googlecloudsdk.calliope import base
from googlecloudsdk.core.console import console_io as io
from googlecloudsdk.shared.pubsub import util
from googlecloudsdk.third_party.apitools.base.py import exceptions as api_ex


class Delete(base.Command):
  """Deletes one or more Cloud Pub/Sub subscriptions."""

  @staticmethod
  def Args(parser):
    """Registers flags for this command."""

    parser.add_argument('subscription', nargs='+',
                        help='One or more subscription names to delete.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      A 2-tuple of lists, one populated with the subscription paths that were
      successfully deleted, the other one with the list of subscription paths
      that could not be deleted.
    """
    msgs = self.context['pubsub_msgs']
    pubsub = self.context['pubsub']

    succeeded = []
    failed = []

    for subscription_name in args.subscription:
      delete_req = msgs.PubsubProjectsSubscriptionsDeleteRequest(
          subscription=util.SubscriptionFormat(subscription_name))
      try:
        pubsub.projects_subscriptions.Delete(delete_req)
        succeeded.append(delete_req.subscription)
      except api_ex.HttpError as e:
        failed.append((delete_req.subscription,
                       json.loads(e.content)['error']['message']))

    return succeeded, failed

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    succeeded, failed = result
    successes = len(succeeded)
    failures = len(failed)

    if successes:
      success_printer = io.ListPrinter(
          '{0} subscription(s) deleted successfully'.format(successes))
      success_printer.Print([subscription for subscription in succeeded])

    if failures:
      fail_printer = io.ListPrinter(
          '{0} subscription(s) failed'.format(failures))
      fail_printer.Print(
          ['{0} (reason: {1})'.format(subs, reason) for subs, reason in failed])

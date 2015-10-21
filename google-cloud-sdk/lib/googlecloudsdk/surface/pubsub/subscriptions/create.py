# Copyright 2015 Google Inc. All Rights Reserved.
"""Cloud Pub/Sub subscription create command."""

import json

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io as io
from googlecloudsdk.shared.pubsub import util
from googlecloudsdk.third_party.apitools.base.py import exceptions as api_ex


class Create(base.Command):
  """Creates one or more Cloud Pub/Sub subscriptions.

  Creates one or more Cloud Pub/Sub subscriptions for a given topic.
  The new subscription defaults to a PULL subscription unless a push endpoint
  is specified.
  """

  @staticmethod
  def Args(parser):
    """Registers flags for this command."""

    parser.add_argument('subscription', nargs='+',
                        help='One or more subscriptions to create.')

    parser.add_argument(
        '--topic', required=True,
        help=('The name of the topic from which this subscription is receiving'
              ' messages. Each subscription is attached to a single topic.'))

    parser.add_argument(
        '--topic-project', default='',
        help=('The name of the project the provided topic belongs to.'
              ' If not set, it defaults to the currently selected'
              ' cloud project.'))

    parser.add_argument(
        '--ack-deadline', type=int, default=10,
        help=('The number of seconds the system will wait for a subscriber to'
              ' acknowledge receiving a message before re-attempting'
              ' delivery.'))

    parser.add_argument(
        '--push-endpoint',
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
      A 2-tuple of lists, one populated with the subscription paths that were
      successfully created, the other one with the list of subscription names
      that could not be created.
    """
    msgs = self.context['pubsub_msgs']
    pubsub = self.context['pubsub']

    succeeded = []
    failed = []

    for subscription in args.subscription:
      create_req = msgs.Subscription(name=util.SubscriptionFormat(subscription),
                                     topic=util.TopicFormat(
                                         args.topic, args.topic_project),
                                     ackDeadlineSeconds=args.ack_deadline)
      if args.push_endpoint:
        create_req.pushConfig = msgs.PushConfig(pushEndpoint=args.push_endpoint)

      try:
        succeeded.append(pubsub.projects_subscriptions.Create(create_req))
      except api_ex.HttpError as exc:
        failed.append((subscription,
                       json.loads(exc.content)['error']['message']))

    return succeeded, failed

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    succeeded, failed = result

    subscription_type = 'pull'
    if args.push_endpoint:
      subscription_type = 'push'

    if succeeded:
      success_printer = io.ListPrinter(
          '{0} {1} subscription(s) created successfully'.format(
              len(succeeded), subscription_type))
      success_printer.Print([subscription.name for subscription in succeeded])

      log.out.Print('for topic "{0}"'.format(
          util.TopicFormat(args.topic, args.topic_project)))

      log.out.Print(
          'Acknowledgement deadline: {0} seconds'.format(args.ack_deadline))

      if args.push_endpoint:
        log.out.Print('Push endpoint: "{0}"'.format(args.push_endpoint))

    if failed:
      fail_printer = io.ListPrinter(
          '{0} subscription(s) failed'.format(len(failed)))
      fail_printer.Print(
          ['{0} (reason: {1})'.format(topic, desc) for topic, desc in failed])

# Copyright 2015 Google Inc. All Rights Reserved.

"""The main command group for Cloud Pub/Sub.

Everything under here will be the commands in your group.  Each file results in
a command with that name.

This module contains a single class that extends base.Group.  Calliope will
dynamically search for the implementing class and use that as the command group
for this command tree.  You can implement methods in this class to override some
of the default behavior.
"""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apis.pubsub.v1 import pubsub_v1_client as cli
from googlecloudsdk.third_party.apis.pubsub.v1 import pubsub_v1_messages


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class Pubsub(base.Group):
  """Manage Cloud Pub/Sub topics and subscriptions."""

  def Filter(self, context, args):
    """Modify the context that will be given to this group's commands when run.

    The context is a dictionary into which you can insert whatever you like.
    The context is given to each command under this group.  You can do common
    initialization here and insert it into the context for later use.  Of course
    you can also do common initialization as a function that can be called in a
    library.

    Args:
      context: {str:object}, A set of key-value pairs that can be used for
          common initialization among commands.
      args: argparse.Namespace: The same namespace given to the corresponding
          .Run() invocation.
    """
    pubsub_url = properties.VALUES.api_endpoint_overrides.pubsub.Get()
    context['pubsub_msgs'] = pubsub_v1_messages
    context['pubsub'] = cli.PubsubV1(url=(pubsub_url or ''),
                                     get_credentials=False,
                                     http=self.Http())

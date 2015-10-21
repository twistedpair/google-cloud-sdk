# Copyright 2015 Google Inc. All Rights Reserved.

"""The main command group for bigtable."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apis.bigtableclusteradmin import v1


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class Bigtable(base.Group):
  """Manage your Cloud Bigtable storage."""

  def Filter(self, context, args):
    """Modify the context that will be given to this group's commands when run.

    Args:
      context: {str:object}, A set of key-value pairs that can be used for
          common initialization among commands.
      args: argparse.Namespace: The same namespace given to the corresponding
          .Run() invocation.
    """
    context['clusteradmin'] = v1.BigtableclusteradminV1(
        get_credentials=False, http=self.Http(),
        url=properties.VALUES.api_endpoint_overrides.bigtableclusteradmin.Get())
    context['clusteradmin-msgs'] = v1.bigtableclusteradmin_v1_messages


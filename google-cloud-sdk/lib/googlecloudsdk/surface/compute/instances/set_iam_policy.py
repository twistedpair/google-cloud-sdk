# Copyright 2015 Google Inc. All Rights Reserved.
"""Command to set IAM policy for an instance resource."""

from googlecloudsdk.api_lib.compute import iam_base_classes
from googlecloudsdk.calliope import base


@base.Hidden
@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class SetIamPolicy(iam_base_classes.ZonalSetIamPolicy):
  """Set the IAM Policy for a Google Compute Engine instance resource."""

  @staticmethod
  def Args(parser):
    iam_base_classes.ZonalSetIamPolicy.Args(parser, 'compute.instances')

  @property
  def service(self):
    return self.compute.instances

  @property
  def resource_type(self):
    return 'instances'

SetIamPolicy.detailed_help = iam_base_classes.SetIamPolicyHelp('instance')

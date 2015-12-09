# Copyright 2015 Google Inc. All Rights Reserved.
"""Command to get IAM policy for a resource."""

from googlecloudsdk.api_lib.compute import iam_base_classes
from googlecloudsdk.calliope import base


@base.Hidden
@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class GetIamPolicy(iam_base_classes.ZonalGetIamPolicy):
  """Command to get IAM policy for an instance resource."""

  @staticmethod
  def Args(parser):
    iam_base_classes.ZonalGetIamPolicy.Args(parser, 'compute.instances')

  @property
  def service(self):
    return self.compute.instances

  @property
  def resource_type(self):
    return 'instances'

GetIamPolicy.detailed_help = iam_base_classes.GetIamPolicyHelp('instance')

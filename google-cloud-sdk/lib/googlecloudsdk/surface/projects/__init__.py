# Copyright 2014 Google Inc. All Rights Reserved.

"""The command group for the Projects CLI."""

import textwrap
import urlparse

from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.third_party.apis.cloudresourcemanager import v1beta1


@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.BETA)
class Projects(base.Group):
  """Manage your Projects.

  Commands to get information about your Google Developer Projects.
  """

  def Filter(self, context, _):
    cloudresourcemanager_client_v1beta1 = v1beta1.CloudresourcemanagerV1beta1(
        url=properties.VALUES.api_endpoint_overrides.cloudresourcemanager.Get(),
        get_credentials=False,
        http=self.Http())
    context['projects_client'] = cloudresourcemanager_client_v1beta1
    context['projects_messages'] = v1beta1
    context['projects_resources'] = resources

# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for listing named ports in instance groups."""
from googlecloudsdk.api_lib.compute import instance_groups_utils


class GetNamedPorts(instance_groups_utils.InstanceGroupGetNamedPorts):
  pass

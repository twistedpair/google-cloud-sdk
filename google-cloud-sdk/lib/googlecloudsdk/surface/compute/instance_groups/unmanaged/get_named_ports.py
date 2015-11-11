# Copyright 2015 Google Inc. All Rights Reserved.
"""instance-groups unmanaged get-named-ports command.

It's an alias for the instance-groups get-named-ports command.
"""
from googlecloudsdk.api_lib.compute import instance_groups_utils


class GetNamedPorts(instance_groups_utils.InstanceGroupGetNamedPorts):
  pass

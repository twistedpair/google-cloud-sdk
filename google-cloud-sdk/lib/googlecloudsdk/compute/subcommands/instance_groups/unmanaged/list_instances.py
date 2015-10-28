# Copyright 2015 Google Inc. All Rights Reserved.
"""managed-instance-groups list-instances command.

It's an alias for the instance-groups list-instances command.
"""
from googlecloudsdk.api_lib.compute import instance_groups_utils


class ListInstances(instance_groups_utils.InstanceGroupListInstances):
  pass

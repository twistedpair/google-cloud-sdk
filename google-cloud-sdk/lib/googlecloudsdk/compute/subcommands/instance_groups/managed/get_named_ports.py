# Copyright 2015 Google Inc. All Rights Reserved.
"""instance-groups managed get-named-ports command.

It's an alias for the instance-groups get-named-ports command.
"""
from googlecloudsdk.compute.subcommands.instance_groups import get_named_ports


class GetNamedPorts(get_named_ports.GetNamedPorts):
  pass


GetNamedPorts.detailed_help = {
    'brief': ('Lists the named ports for a managed instance group'),
    'DESCRIPTION': """\
Named ports are key:value pairs metadata representing the service name and the
port that it's running on. Named ports can be assigned to an instance group,
which indicates that the service is available on all instances in the group.
This information is used by the HTTP Load Balancing service.

For example, to list named ports (name and port tuples) for a managed instance
group:

  $ {command} example-instance-group --zone us-central1-a

The above example lists named ports assigned to an instance group named
``example-instance-group'' in the ``us-central1-a'' zone.
""",
}

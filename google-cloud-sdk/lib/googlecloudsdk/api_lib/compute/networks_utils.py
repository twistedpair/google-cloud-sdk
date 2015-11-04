# Copyright 2015 Google Inc. All Rights Reserved.
"""Code that's shared between multiple networks subcommands."""


def _GetNetworkMode(network):
  """Takes a network resource and returns the "mode" of the network."""
  if network.get('IPv4Range', None) is not None:
    return 'legacy'
  if network.get('autoCreateSubnetworks', False):
    return 'auto'
  else:
    return 'custom'


def AddMode(items):
  for resource in items:
    resource['x_gcloud_mode'] = _GetNetworkMode(resource)
    yield resource

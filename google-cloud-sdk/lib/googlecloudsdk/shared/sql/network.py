# Copyright 2015 Google Inc. All Rights Reserved.

"""Common utility functions for network operations."""

import ipaddr

IP_VERSION_4 = 4
IP_VERSION_6 = 6
IP_VERSION_UNKNOWN = 0


def GetIpVersion(ip_address):
  """Given an ip address, determine IP version.

  Args:
    ip_address: string, IP address to test IP version of

  Returns:
    int, the IP version if it could be determined or IP_VERSION_UNKNOWN
    otherwise.
  """
  try:
    version = ipaddr.IPAddress(ip_address).version
    if version not in (IP_VERSION_4, IP_VERSION_6):
      raise ValueError('Reported IP version not recognized.')
    return version
  except ValueError:  # ipaddr library could not resolve address
    return IP_VERSION_UNKNOWN

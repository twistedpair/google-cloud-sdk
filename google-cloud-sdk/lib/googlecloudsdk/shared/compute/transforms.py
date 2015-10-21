# Copyright 2015 Google Inc. All Rights Reserved.

"""Compute resource transforms and symbols dict.

NOTICE: Each TransformFoo() method is the implementation of a foo() transform
function. Even though the implementation here is in Python the usage in resource
projection and filter expressions is language agnostic. This affects the
Pythonicness of the Transform*() methods:
  (1) The docstrings are used to generate external user documentation.
  (2) The method prototypes are included in the documentation. In particular the
      prototype formal parameter names are stylized for the documentation.
  (3) The types of some args, like r, are not fixed until runtime. Other args
      may have either a base type value or string representation of that type.
      It is up to the transform implementation to silently do the string=>type
      conversions. That's why you may see e.g. int(arg) in some of the methods.
  (4) Unless it is documented to do so, a transform function must not raise any
      exceptions. The `undefined' arg is used to handle all unusual conditions,
      including ones that would raise exceptions.
"""

import httplib

from googlecloudsdk.core.resource import resource_transform
from googlecloudsdk.shared.compute import constants


def TransformFirewallRule(r):
  """Returns a compact string describing the firewall rule in r.

  The compact string is a comma-separated list of PROTOCOL:PORT_RANGE items.
  If a particular protocol has no port ranges then only the protocol is listed.

  Args:
    r: JSON-serializable object.

  Returns:
    A compact string describing the firewall rule in r.
  """
  protocol = r.get('IPProtocol', None)
  if protocol is None:
    return ''
  rule = []
  port_ranges = r.get('ports', None)
  if port_ranges is None:
    rule.append(protocol)
  else:
    for port_range in port_ranges:
      rule.append('{0}:{1}'.format(protocol, port_range))
  return ','.join(rule)


def TransformImageAlias(r):
  """Returns a comma-separated list of alias names for the image in r.

  Args:
    r: JSON-serializable object.

  Returns:
    A comma-separated list of alias names for the image in r.
  """
  name = r.get('name', None)
  if name is None:
    return ''
  project = resource_transform.TransformScope(
      r.get('selfLink', ''), 'projects').split('/')[0]
  aliases = [alias for alias, value in constants.IMAGE_ALIASES.items()
             if name.startswith(value.name_prefix)
             and value.project == project]
  return ','.join(aliases)


def TransformNextMaintenance(r):
  """Returns the timestamps of the next scheduled maintenance or ''.

  All timestamps are assumed to be ISO strings in the same timezone.

  Args:
    r: JSON-serializable object.

  Returns:
    The timestamps of the next scheduled maintenance or ''.
  """
  if not r:
    return ''
  next_event = min(r, key=lambda x: x.get('beginTime', None))
  if next_event is None:
    return ''
  begin_time = next_event.get('beginTime', None)
  if begin_time is None:
    return ''
  end_time = next_event.get('endTime', None)
  if end_time is None:
    return ''
  return '{0}--{1}'.format(begin_time, end_time)


def TransformOperationHttpStatus(r):
  """Returns the HTTP response code of the operation in r.

  Args:
    r: JSON-serializable object.

  Returns:
    The HTTP response code of the operation in r.
  """
  if r.get('status', None) == 'DONE':
    return r.get('httpErrorStatusCode', None) or httplib.OK
  return ''


def TransformQuota(r):
  """Formats the quota in r as usage/limit.

  Args:
    r: JSON-serializable object.

  Returns:
    The quota in r as usage/limit.
  """
  if not r:
    return ''
  usage = r.get('usage', None)
  if usage is None:
    return ''
  limit = r.get('limit', None)
  if limit is None:
    return ''
  try:
    if usage == int(usage) and limit == int(limit):
      return '{0}/{1}'.format(int(usage), int(limit))
    return '{0:.2f}/{1:.2f}'.format(usage, limit)
  except (TypeError, ValueError):
    return ''


def TransformStatus(r):
  """Returns the machine status in r with deprecation information if applicable.

  Args:
    r: JSON-serializable object.

  Returns:
    The machine status in r with deprecation information if applicable.
  """
  status = r.get('status', None)
  deprecated = r.get('deprecated', '')
  if deprecated:
    return '{0} ({1})'.format(status, deprecated.get('state', ''))
  return status or ''


_TRANSFORMS = {

    'firewall_rule': TransformFirewallRule,
    'image_alias': TransformImageAlias,
    'next_maintenance': TransformNextMaintenance,
    'operation_http_status': TransformOperationHttpStatus,
    'quota': TransformQuota,
    'status': TransformStatus,
}


def GetTransforms():
  """Returns the compute specific resource transform symbol table."""
  return _TRANSFORMS

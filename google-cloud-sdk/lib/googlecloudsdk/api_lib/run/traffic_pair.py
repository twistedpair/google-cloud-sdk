# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Wrapper for Cloud Run TrafficTargets messages."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


from googlecloudsdk.api_lib.run import traffic


# Human readable indicator for a missing traffic percentage.
_MISSING_PERCENT = '-'


def _FormatPercentage(percent):
  if percent == _MISSING_PERCENT:
    return _MISSING_PERCENT
  else:
    return '{}%'.format(percent)


class TrafficTargetPair(object):
  """Holder for a TrafficTarget status information.

  The representation of the status of traffic for a service
  includes:
    o User requested assignments (spec.traffic)
    o Actual assignments (status.traffic)

  These may differ after a failed traffic update or during a
  successful one. A TrafficTargetPair holds both values
  for a TrafficTarget, identified by revisionName or by
  latestRevision. In cases a TrafficTarget is added or removed
  from a service, either value can be missing.

  The latest revision can be included in the spec traffic targets
  twice
    o by revisionName
    o by setting latestRevision to True.

  Managed cloud run provides a single combined status traffic target
  for both spec entries with:
    o revisionName set to the latest revision's name
    o percent set to combined percentage for both spec entries
    o latestRevision not set

  In this case both spec targets are paired with the combined status
  target and a status_percent_override value is used to allocate the
  combined traffic.
  """

  def __init__(
      self, spec_target, status_target, latest_revision_name,
      status_percent_override):
    self._spec_target = spec_target
    self._status_target = status_target
    self._latest_revision_name = latest_revision_name
    self._status_percent_override = status_percent_override

  @property
  def key(self):
    return (traffic.LATEST_REVISION_KEY
            if self.latestRevision else traffic.GetKey(self))

  @property
  def latestRevision(self):  # pylint: disable=invalid-name
    result = False
    if self._spec_target and self._spec_target.latestRevision:
      result = True
    if self._status_target and self._status_target.latestRevision:
      result = True
    return result

  @property
  def revisionName(self):  # pylint: disable=invalid-name
    result = None
    if self._spec_target and self._spec_target.revisionName:
      result = self._spec_target.revisionName
    if self._status_target and self._status_target.revisionName:
      result = self._status_target.revisionName
    return result

  @property
  def specTarget(self):  # pylint: disable=invalid-name
    return self._spec_target

  @property
  def statusTarget(self):  # pylint: disable=invalid-name
    return self._status_target

  @property
  def specPercent(self):  # pylint: disable=invalid-name
    if self._spec_target:
      return str(self._spec_target.percent)
    else:
      return _MISSING_PERCENT

  @property
  def statusPercent(self):  # pylint: disable=invalid-name
    if self._status_percent_override is not None:
      return str(self._status_percent_override)
    elif self._status_target:
      return str(self._status_target.percent)
    return _MISSING_PERCENT

  @property
  def displayPercent(self):  # pylint: disable=invalid-name
    """Returns human readable revision percent."""

    if self.statusPercent == self.specPercent:
      return _FormatPercentage(self.statusPercent)
    else:
      return '{:4} (currently {})'.format(
          _FormatPercentage(self.specPercent),
          _FormatPercentage(self.statusPercent))

  @property
  def displayRevisionId(self):  # pylint: disable=invalid-name
    """Returns human readable revision identifier."""
    if self.latestRevision:
      return '%s (currently %s)' % (traffic.GetKey(self),
                                    self._latest_revision_name)
    else:
      return self.revisionName

  def SetSpecTarget(self, target):
    self._spec_target = target

  def SetStatusTarget(self, target, inferred_latest=False):
    self._status_target = target
    self._inferred_latest = inferred_latest


def GetTrafficTargetPairs(spec_targets, status_targets, is_platform_managed,
                          latest_ready_revision_name):
  """Returns the list of TrafficTargetPair's for a Service."""
  spec_dict = {traffic.GetKey(t): t for t in spec_targets}
  status_dict = {traffic.GetKey(t): t for t in status_targets}

  # For managed the status target for the latest revision is
  # included by revisionName only and may hold the combined traffic
  # percent for both latestRevisionName and latestRevision spec targets.
  # Here we adjust keys in status_dict to match with spec_dict.
  combined_status_target_id = None
  if (is_platform_managed and traffic.LATEST_REVISION_KEY in spec_dict and
      traffic.LATEST_REVISION_KEY not in status_dict and
      latest_ready_revision_name in status_dict):
    latest_status_target = status_dict[latest_ready_revision_name]
    status_dict[traffic.LATEST_REVISION_KEY] = latest_status_target
    if latest_ready_revision_name in spec_dict:
      combined_status_target_id = id(latest_status_target)
    else:
      del status_dict[latest_ready_revision_name]
  result = []
  for k in set(spec_dict).union(status_dict):
    spec_target = spec_dict.get(k, None)
    status_target = status_dict.get(k, None)
    percent_override = None
    if id(status_target) == combined_status_target_id:
      spec_by_latest_target = spec_dict[traffic.LATEST_REVISION_KEY]
      status_by_latest_percent = min(
          spec_by_latest_target.percent, status_target.percent)
      if k == traffic.LATEST_REVISION_KEY:
        percent_override = status_by_latest_percent
      else:
        percent_override = status_target.percent - status_by_latest_percent
    result.append(TrafficTargetPair(
        spec_target, status_target, latest_ready_revision_name,
        percent_override))
  return sorted(result, key=traffic.SortKeyFromTarget)

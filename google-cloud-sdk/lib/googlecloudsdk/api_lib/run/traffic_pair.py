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

import six


# Human readable indicator for a missing traffic percentage.
_MISSING_PERCENT = '-'


def _FormatPercentage(percent):
  if percent == _MISSING_PERCENT:
    return _MISSING_PERCENT
  else:
    return '{}%'.format(percent)


class TrafficTargetPair(object):
  """Holder for TrafficTarget status information.

  The representation of the status of traffic for a service
  includes:
    o User requested assignments (spec.traffic)
    o Actual assignments (status.traffic)

  Each of spec.traffic and status.traffic may contain multiple traffic targets
  that reference the same revision, either directly by name or indirectly by
  referencing the latest ready revision.

  The spec and status traffic targets for a revision may differ after a failed
  traffic update or during a successful one. A TrafficTargetPair holds all
  spec and status TrafficTargets that reference the same revision by name or
  reference the latest ready revision. Both the spec and status traffic targets
  can be empty.

  The latest revision can be included in the spec traffic targets
  two ways
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

  Attributes:
    key: Either the referenced revision name or 'LATEST' if the traffic targets
      reference the latest ready revision.
    latestRevision: Boolean indicating if the traffic targets reference the
      latest ready revision.
    revisionName: The name of the revision referenced by these traffic targets.
    specPercent: The percent of traffic allocated to the referenced revision
      in the service's spec.
    statusPercent: The percent of traffic allocated to the referenced revision
      in the service's status.
    displayPercent: Human-readable representation of the current percent
      assigned to the referenced revision.
    displayRevisionId: Human-readable representation of the name of the
      referenced revision.
  """

  def __init__(
      self, spec_targets, status_targets, revision_name, latest,
      status_percent_override):
    """Creates a new TrafficTargetPair.

    Args:
      spec_targets: A list of spec TrafficTargets that all reference the same
        revision, either by name or the latest ready.
      status_targets: A list of status TrafficTargets that all reference the
        same revision, either by name or the latest ready.
      revision_name: The name of the revision referenced by the traffic targets.
      latest: A boolean indicating if these traffic targets reference the latest
        ready revision.
      status_percent_override: Percent to use for the status percent of this
        TrafficTargetPair, overriding the values in status_targets.

    Returns:
      A new TrafficTargetPair instance.
    """
    self._spec_targets = spec_targets
    self._status_targets = status_targets
    self._revision_name = revision_name
    self._latest = latest
    self._status_percent_override = status_percent_override

  @property
  def key(self):
    return (traffic.LATEST_REVISION_KEY
            if self.latestRevision else traffic.GetKey(self))

  @property
  def latestRevision(self):  # pylint: disable=invalid-name
    """Returns true if the traffic targets reference the latest revision."""
    return self._latest

  @property
  def revisionName(self):  # pylint: disable=invalid-name
    return self._revision_name

  @property
  def specPercent(self):  # pylint: disable=invalid-name
    if self._spec_targets:
      return six.text_type(
          sum(t.percent for t in self._spec_targets if t.percent))
    else:
      return _MISSING_PERCENT

  @property
  def statusPercent(self):  # pylint: disable=invalid-name
    if self._status_percent_override is not None:
      return six.text_type(self._status_percent_override)
    elif self._status_targets:
      return six.text_type(
          sum(t.percent for t in self._status_targets if t.percent))
    else:
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
                                    self.revisionName)
    else:
      return self.revisionName


def _SplitManagedLatestStatusTarget(spec_dict, status_dict, is_platform_managed,
                                    latest_ready_revision_name):
  """Splits the fully-managed latest status target.

  For managed the status target for the latest revision is
  included by revisionName only and may hold the combined traffic
  percent for both latestRevisionName and latestRevision spec targets.
  Here we adjust keys in status_dict to match with spec_dict.

  Args:
    spec_dict: Dictionary mapping revision name or 'LATEST' to the spec
      traffic target referencing that revision.
    status_dict: Dictionary mapping revision name or 'LATEST' to the status
      traffic target referencing that revision. Modified by this function.
    is_platform_managed: Boolean indicating if the current platform is Cloud Run
      fully-managed.
    latest_ready_revision_name: The name of the latest ready revision.

  Returns:
    Optionally, the id of the status target containing the combined traffic
    referencing the latest ready revision by name and by latest.
  """
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
  return combined_status_target_id


def _PercentOverride(key, spec_dict, status_target, combined_status_target_id):
  """Computes the optional override percent to apply to the status percent."""
  percent_override = None
  if id(status_target) == combined_status_target_id:
    spec_by_latest_target = spec_dict[traffic.LATEST_REVISION_KEY]
    status_by_latest_percent = min(spec_by_latest_target.percent,
                                   status_target.percent)
    if key == traffic.LATEST_REVISION_KEY:
      percent_override = status_by_latest_percent
    else:
      percent_override = status_target.percent - status_by_latest_percent
  return percent_override


def GetTrafficTargetPairs(spec_targets, status_targets, is_platform_managed,
                          latest_ready_revision_name):
  """Returns a list of TrafficTargetPairs for a Service.

  Given the list of spec traffic targets and status traffic targets for a
  sevice, this function pairs up all spec and status traffic targets that
  reference the same revision (either by name or the latest ready revision) into
  TrafficTargetPairs. This allows the caller to easily see any differences
  between the spec and status traffic.

  For fully-managed Cloud Run, the status target for the latest revision is
  included by revisionName only and may hold the combined traffic
  percent for both latestRevisionName and latestRevision spec targets. This
  function splits the fully-managed status target for the latest revision into
  a target for the percent allocated to the latest revision by name and a target
  for the percent allocated to the latest revision because it is latest.

  Args:
    spec_targets: An iterable of TrafficTarget protos from the service's spec.
    status_targets: An iterable of TrafficTarget protos from the service's
      status.
    is_platform_managed: Boolean indicating whether the current platform is
      fully-managed or Anthos/GKE.
    latest_ready_revision_name: The name of the service's latest ready revision.
  Returns:
    A list of TrafficTargetPairs representing the current state of the service's
    traffic assignments. The TrafficTargetPairs are sorted by revision name,
    with targets referencing the latest ready revision at the end.
  """
  spec_dict = {traffic.GetKey(t): t for t in spec_targets}
  status_dict = {traffic.GetKey(t): t for t in status_targets}

  combined_status_target_id = _SplitManagedLatestStatusTarget(
      spec_dict, status_dict, is_platform_managed, latest_ready_revision_name)
  result = []
  for k in set(spec_dict).union(status_dict):
    spec_target = spec_dict.get(k, None)
    status_target = status_dict.get(k, None)
    percent_override = _PercentOverride(k, spec_dict, status_target,
                                        combined_status_target_id)
    if k == traffic.LATEST_REVISION_KEY:
      revision_name = latest_ready_revision_name
      latest = True
    else:
      revision_name = k
      latest = False

    # TODO(b/148901171) Temporary conversion until the callers of
    # GetTrafficTargetPairs are updated to pass the traffic targets wrapped in
    # traffic.TrafficTargets instead of the raw traffic target messages.
    to_list = lambda x: [x] if x else []

    result.append(
        TrafficTargetPair(
            to_list(spec_target), to_list(status_target), revision_name, latest,
            percent_override))
  return sorted(result, key=traffic.SortKeyFromTarget)

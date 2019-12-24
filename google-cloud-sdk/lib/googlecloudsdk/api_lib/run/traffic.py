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
"""Wrapper fors a Cloud Run TrafficTargets messages."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import collections

from googlecloudsdk.core import exceptions


class InvalidTrafficSpecificationError(exceptions.Error):
  """Error to indicate an invalid traffic specification."""
  pass


# Designated key value for latest.
# Revisions' names may not be uppercase, so this is distinct.
LATEST_REVISION_KEY = 'LATEST'


def NewTrafficTarget(messages, key, percent):
  if key == LATEST_REVISION_KEY:
    result = messages.TrafficTarget(
        latestRevision=True,
        percent=percent)
  else:
    result = messages.TrafficTarget(
        revisionName=key,
        percent=percent)
  return result


def GetKey(target):
  """Returns the key for a TrafficTarget.

  Args:
    target: TrafficTarget, the TrafficTarget to check

  Returns:
    LATEST_REVISION_KEY if target is for the latest revison or
    target.revisionName if not.
  """
  return LATEST_REVISION_KEY if target.latestRevision else target.revisionName


def SortKeyFromKey(key):
  """Sorted key function  to order TrafficTarget keys.

  TrafficTargets keys are one of:
  o revisionName
  o LATEST_REVISION_KEY

  Note LATEST_REVISION_KEY is not a str so its ordering with respect
  to revisionName keys is hard to predict.

  Args:
    key: Key for a TrafficTargets dictionary.

  Returns:
    A value that sorts by revisionName with LATEST_REVISION_KEY
    last.
  """
  if key == LATEST_REVISION_KEY:
    result = (2, key)
  else:
    result = (1, key)
  return result


def SortKeyFromTarget(target):
  """Sorted key function to order TrafficTarget objects by key.

  Args:
    target: A TrafficTarget.

  Returns:
    A value that sorts by revisionName with LATEST_REVISION_KEY
    last.
  """
  key = GetKey(target)
  return SortKeyFromKey(key)


def NewRoundingCorrectionPrecedence(key_and_percent):
  """Returns object that sorts in the order we correct traffic rounding errors.

  The caller specifies explicit traffic percentages for some revisions and
  this module scales traffic for remaining revisions that are already
  serving traffic up or down to assure that 100% of traffic is assigned.
  This scaling can result in non integrer percentages that Cloud Run
  does not supprt. We correct by:
    - Trimming the decimal part of float_percent, int(float_percent)
    - Adding an extra 1 percent traffic to enough revisions that have
      had their traffic reduced to get us to 100%

  The returned value sorts in the order we correct revisions:
    1) Revisions with a bigger loss due are corrected before revisions with
       a smaller loss. Since 0 <= loss < 1 we sort by the value:  1 - loss.
    2) In the case of ties revisions with less traffic are corrected before
       revisions with more traffic.
    3) In case of a tie revisions with a smaller key are corrected before
       revisions with a larger key.

  Args:
    key_and_percent: tuple with (key, float_percent)

  Returns:
    An value that sorts with respect to values returned for
    other revisions in the order we correct for rounding
    errors.
  """
  key, float_percent = key_and_percent
  return [
      1 - (float_percent - int(float_percent)),
      float_percent,
      SortKeyFromKey(key)]


class TrafficTargets(collections.MutableMapping):
  """Wraps a repeated TrafficTarget message and provides dict-like access.

  The dictionary key is one of
     LATEST_REVISION_KEY for the latest revision
     TrafficTarget.revisionName for TrafficTargets with a revision name.

  """

  def __init__(
      self, messages_module, to_wrap):
    """Constructor.

    Args:
      messages_module: The message module that defines TrafficTarget.
      to_wrap: The traffic targets to wrap.
    """
    self._messages = messages_module
    self._m = to_wrap
    self._traffic_target_cls = self._messages.TrafficTarget

  def __getitem__(self, key):
    """Implements evaluation of `self[key]`."""
    for target in self._m:
      if key == GetKey(target):
        return target
    raise KeyError(key)

  def __setitem__(self, key, new_target):
    """Implements evaluation of `self[key] = target`."""
    for index, target in enumerate(self._m):
      if key == GetKey(target):
        self._m[index] = new_target
        break
    else:
      self._m.append(new_target)

  def __delitem__(self, key):
    """Implements evaluation of `del self[key]`."""
    index_to_delete = 0
    for index, target in enumerate(self._m):
      if key == GetKey(target):
        index_to_delete = index
        break
    else:
      raise KeyError(key)

    del self._m[index_to_delete]

  def __contains__(self, key):
    """Implements evaluation of `item in self`."""
    for target in self._m:
      if key == GetKey(target):
        return True
    return False

  def __len__(self):
    """Implements evaluation of `len(self)`."""
    return len(self._m)

  def __iter__(self):
    """Returns a generator yielding the env var keys."""
    for target in self._m:
      yield GetKey(target)

  def MakeSerializable(self):
    return self._m

  def __repr__(self):
    content = ', '.join('{}: {}'.format(k, v) for k, v in self.items())
    return '[%s]' % content

  def _ValidateCurrentTraffic(self):
    percent = 0
    for target in self._m:
      percent += target.percent

    if percent != 100:
      raise ValueError(
          'Current traffic allocation of %s is not 100 percent' % percent)

    for target in self._m:
      if target.percent < 0:
        raise ValueError(
            'Current traffic for target %s is negative (%s)' % (
                GetKey(target), target.percent))

  def _GetUnassignedTargets(self, new_percentages):
    """Get TrafficTargets with traffic not in new_percentages."""
    result = {}
    for target in self._m:
      key = GetKey(target)
      if target.percent and key not in new_percentages:
        result[key] = target
    return result

  def _IsChangedPercentages(self, new_percentages):
    """Returns True iff new_percentages changes current traffic."""
    old_percentages = {GetKey(target): target.percent for target in self._m}
    for key in new_percentages:
      if (key not in old_percentages or
          new_percentages[key] != old_percentages[key]):
        return True
    return False

  def _ValidateNewPercentages(self, new_percentages, unspecified_targets):
    """Validate the new traffic percentages the user specified."""
    specified_percent = sum(new_percentages.values())
    if specified_percent > 100:
      raise InvalidTrafficSpecificationError(
          'Over 100% of traffic is specified.')

    for key in new_percentages:
      if new_percentages[key] < 0 or new_percentages[key] > 100:
        raise InvalidTrafficSpecificationError(
            'New traffic for target %s is %s, not between 0 and 100' % (
                key, new_percentages[key]))

    if not unspecified_targets and specified_percent < 100:
      raise InvalidTrafficSpecificationError(
          'Every target with traffic is updated but 100% of '
          'traffic has not been specified.')

  def _GetPercentUnspecifiedTraffic(self, new_percentages):
    """Returns percentage of traffic not explicitly specified by caller."""
    specified_percent = sum(new_percentages.values())
    return 100 - specified_percent

  def _IntPercentages(self, float_percentages):
    rounded_percentages = {
        k: int(float_percentages[k]) for k in float_percentages}
    loss = int(round(sum(float_percentages.values()))) - sum(
        rounded_percentages.values())
    correction_precedence = sorted(
        float_percentages.items(),
        key=NewRoundingCorrectionPrecedence)
    for key, _ in correction_precedence[:loss]:
      rounded_percentages[key] += 1
    return rounded_percentages

  def _GetAssignedPercentages(self, new_percentages, unassigned_targets):
    percent_to_assign = self._GetPercentUnspecifiedTraffic(new_percentages)
    if percent_to_assign == 0:
      return {}
    percent_to_assign_from = sum(
        target.percent for target in unassigned_targets.values())
    #
    # We assign traffic to unassigned targests (were seving and
    # have not explicit new percentage assignent). The assignment
    # is proportional to the original traffic for the each target.
    #
    # percent_to_assign
    #    == percent_to_assign_from * (
    #          percent_to_assign)/percent_to_assign_from)
    #    == sum(unassigned_targets[k].percent) * (
    #          percent_to_assign)/percent_to_assign_from)
    #    == sum(unassigned_targets[k].percent] *
    #          percent_to_assign)/percent_to_assign_from)
    assigned_percentages = {}
    for k in unassigned_targets:
      assigned_percentages[k] = unassigned_targets[k].percent * float(
          percent_to_assign)/percent_to_assign_from
    return assigned_percentages

  def UpdateTraffic(self, new_percentages):
    """Update traffic assignments.

    The updated traffic assignments will include assignments explicitly
    specified by the caller. If the caller does not assign 100% of
    traffic explicitly this function will scale traffic for targets
    the user does not specify up or down based on the provided
    assignments as needed.

    The update removes targets with 0% traffic unless:
     o The user explicitly specifies under 100% of total traffic
     o The user does not explicitly specify 0% traffic for the target.

    Args:
      new_percentages: Dict[str, int], Map from revision to percent
        traffic for the revision. 'LATEST' means the latest rev.
    Raises:
      ValueError: If the current traffic for the service is invalid.
      InvalidTrafficSpecificationError: If the caller attempts to set
        the traffic for the service to an incorrect state.
    """
    self._ValidateCurrentTraffic()
    original_targets = {GetKey(target): target for target in self._m}
    updated_percentages = new_percentages.copy()
    unassigned_targets = self._GetUnassignedTargets(updated_percentages)
    self._ValidateNewPercentages(updated_percentages, unassigned_targets)
    updated_percentages.update(
        self._GetAssignedPercentages(updated_percentages, unassigned_targets))
    int_percentages = self._IntPercentages(updated_percentages)
    new_targets = []
    for key in int_percentages:
      if key in new_percentages and new_percentages[key] == 0:
        continue
      elif key in original_targets:
        # Preserve state of retained targets.
        target = original_targets[key]
        target.percent = int_percentages[key]
      else:
        target = NewTrafficTarget(self._messages, key, int_percentages[key])
      new_targets.append(target)
    new_targets = sorted(new_targets, key=SortKeyFromTarget)
    del self._m[:]
    self._m.extend(new_targets)

  def ZeroLatestTraffic(self, latest_ready_revision_name):
    """Reasign traffic from LATEST to the current latest revision."""
    targets = {GetKey(target): target for target in self._m}
    if LATEST_REVISION_KEY in targets and targets[LATEST_REVISION_KEY].percent:
      latest = targets.pop(LATEST_REVISION_KEY)
      if latest_ready_revision_name in targets:
        targets[latest_ready_revision_name].percent += latest.percent
      else:
        targets[latest_ready_revision_name] = NewTrafficTarget(
            self._messages, latest_ready_revision_name, latest.percent)
      sorted_targets = [targets[k] for k in sorted(targets, key=SortKeyFromKey)]
      del self._m[:]
      self._m.extend(sorted_targets)

# Human readable indicator for a missing traffic percentage.
_MISSING_PERCENT = '-'


def FormatPercentage(percent):
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
    return LATEST_REVISION_KEY if self.latestRevision else GetKey(self)

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
      return FormatPercentage(self.statusPercent)
    else:
      return '{:4} (currently {})'.format(
          FormatPercentage(self.specPercent),
          FormatPercentage(self.statusPercent))

  @property
  def displayRevisionId(self):  # pylint: disable=invalid-name
    """Returns human readable revision identifier."""
    if self.latestRevision:
      return '%s (currently %s)'% (GetKey(self), self._latest_revision_name)
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
  spec_dict = {GetKey(t): t for t in spec_targets}
  status_dict = {GetKey(t): t for t in status_targets}

  # For managed the status target for the latest revision is
  # included by revisionName only and may hold the combined traffic
  # percent for both latestRevisionName and latestRevision spec targets.
  # Here we adjust keys in status_dict to match with spec_dict.
  combined_status_target_id = None
  if (is_platform_managed
      and LATEST_REVISION_KEY in spec_dict
      and LATEST_REVISION_KEY not in status_dict
      and latest_ready_revision_name in status_dict):
    latest_status_target = status_dict[latest_ready_revision_name]
    status_dict[LATEST_REVISION_KEY] = latest_status_target
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
      spec_by_latest_target = spec_dict[LATEST_REVISION_KEY]
      status_by_latest_percent = min(
          spec_by_latest_target.percent, status_target.percent)
      if k == LATEST_REVISION_KEY:
        percent_override = status_by_latest_percent
      else:
        percent_override = status_target.percent - status_by_latest_percent
    result.append(TrafficTargetPair(
        spec_target, status_target, latest_ready_revision_name,
        percent_override))
  return sorted(result, key=SortKeyFromTarget)

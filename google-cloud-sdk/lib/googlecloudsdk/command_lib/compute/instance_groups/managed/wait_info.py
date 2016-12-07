# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Wait messages for the compute instance groups managed commands."""


_CURRENT_ACTION_TYPES = ['abandoning', 'creating', 'creatingWithoutRetries',
                         'deleting', 'recreating', 'refreshing', 'restarting',
                         'verifying']


_PENDING_ACTION_TYPES = ['creating', 'deleting', 'restarting', 'recreating']


def IsGroupStable(igm_ref):
  """Checks if IGM is has no current actions on instances.

  Args:
    igm_ref: reference to the Instance Group Manager.
  Returns:
    True if IGM has no current actions, false otherwise.
  """
  return not any(getattr(igm_ref.currentActions, action, 0)
                 for action in _CURRENT_ACTION_TYPES)


def IsGroupStableAlpha(igm_ref):
  """Checks if IGM is has no current or pending actions on instances.

  Args:
    igm_ref: reference to the Instance Group Manager.
  Returns:
    True if IGM has no current actions, false otherwise.
  """
  no_current_actions = not any(getattr(igm_ref.currentActions, action, 0)
                               for action in _CURRENT_ACTION_TYPES)
  no_pending_actions = not any(getattr(igm_ref.pendingActions, action, 0)
                               for action in _PENDING_ACTION_TYPES)
  return no_current_actions and no_pending_actions


def CreateWaitText(igm_ref):
  """Creates text presented at each wait operation.

  Args:
    igm_ref: reference to the Instance Group Manager.
  Returns:
    A message with current operations count for IGM.
  """
  text = 'Waiting for group to become stable'
  current_actions_text = _CreateActionsText(
      ', current operations: ',
      igm_ref.currentActions,
      _CURRENT_ACTION_TYPES)
  return text + current_actions_text


def CreateWaitTextAlpha(igm_ref):
  """Creates text presented at each wait operation.

  Args:
    igm_ref: reference to the Instance Group Manager.
  Returns:
    A message with current and pending operations count for IGM.
  """
  text = 'Waiting for group to become stable'
  current_actions_text = _CreateActionsText(
      ', current operations: ',
      igm_ref.currentActions,
      _CURRENT_ACTION_TYPES)
  pending_actions_text = _CreateActionsText(
      ', pending operations: ',
      igm_ref.pendingActions,
      _PENDING_ACTION_TYPES)
  return text + current_actions_text + pending_actions_text


def _CreateActionsText(text, igm_field, action_types):
  """Creates text presented at each wait operation for given IGM field.

  Args:
    text: the text associated with the field.
    igm_field: reference to a field in the Instance Group Manager.
    action_types: array with field values to be counted.
  Returns:
    A message with given field and action types count for IGM.
  """
  actions = []
  for action in action_types:
    action_count = getattr(igm_field, action, 0)
    if action_count > 0:
      actions.append('{0}: {1}'.format(action, action_count))
  return text + ','.join(actions) if actions else ''

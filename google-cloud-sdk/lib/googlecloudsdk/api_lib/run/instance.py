# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Wraps a Cloud Run Instance message with convenience methods."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import enum

from googlecloudsdk.api_lib.run import container_resource
from googlecloudsdk.api_lib.run import k8s_object
from googlecloudsdk.core.console import console_attr


class InstanceStatus(enum.Enum):
  PENDING = 'pending'
  RUNNING = 'running'
  STOPPED = 'stopped'
  COMPLETED = 'completed'
  FAILED = 'failed'
  UNKNOWN = 'unknown'


class InstanceSymbol:
  """A class to represent the symbol and color for an instance."""

  def __init__(self, best, alt, color=None):
    self.best = best
    self.alt = alt
    self.color = color


class Instance(container_resource.ContainerResource):
  """Wraps a Cloud Run instance message, making fields more convenient."""

  API_CATEGORY = 'run.googleapis.com'
  KIND = 'Instance'
  READY_CONDITION = 'Running'

  ELLIPSIS_SYMBOL = '\N{HORIZONTAL ELLIPSIS}'
  PLAY_SYMBOL = '\N{BLACK RIGHT-POINTING TRIANGLE}'
  PAUSED_SYMBOL = '\N{DOUBLE VERTICAL BAR}'
  CHECK_MARK_SYMBOL = '\N{HEAVY CHECK MARK}'

  INSTANCE_SYMBOLS = {
      InstanceStatus.PENDING: InstanceSymbol(
          best=ELLIPSIS_SYMBOL, alt='.', color='yellow'
      ),
      InstanceStatus.RUNNING: InstanceSymbol(
          best=PLAY_SYMBOL, alt='+', color='green'
      ),
      InstanceStatus.STOPPED: InstanceSymbol(
          best=PAUSED_SYMBOL, alt='-', color='blue'
      ),
      InstanceStatus.COMPLETED: InstanceSymbol(best=CHECK_MARK_SYMBOL, alt='+'),
      InstanceStatus.FAILED: InstanceSymbol(best='X', alt='X', color='red'),
  }

  def _EnsureNodeSelector(self):
    if self.spec.nodeSelector is None:
      self.spec.nodeSelector = k8s_object.InitializedInstance(
          self._messages.InstanceSpec.NodeSelectorValue
      )

  @property
  def is_running(self):
    return self.conditions.get('Running', False)

  @property
  def template(self):
    return self

  @property
  def node_selector(self):
    """The node selector as a dictionary { accelerator_type: value}."""
    self._EnsureNodeSelector()
    return k8s_object.KeyValueListAsDictionaryWrapper(
        self.spec.nodeSelector.additionalProperties,
        self._messages.InstanceSpec.NodeSelectorValue.AdditionalProperty,
        key_field='key',
        value_field='value',
    )

  @property
  def urls(self):
    """Return the URLs of this instance."""
    if self._m.status and self._m.status.urls:
      return self._m.status.urls
    return []

  @property
  def status(self):
    """Return the status of this instance."""
    ready_cond = self.conditions.get(self.READY_CONDITION, None)
    if ready_cond and ready_cond['status']:
      # Running
      return InstanceStatus.RUNNING
    elif ready_cond and not ready_cond['status']:
      if not ready_cond.get('reason'):
        # Done
        return InstanceStatus.COMPLETED
      elif ready_cond.get('reason') == 'Stopped':
        # Paused
        return InstanceStatus.STOPPED
      else:
        # Failed
        return InstanceStatus.FAILED
    else:
      # Pending
      return InstanceStatus.PENDING

  def ReadySymbolAndColor(self):
    """Return a tuple of ready_symbol and display color for this object."""
    status = self.status
    encoding = console_attr.GetConsoleAttr().GetEncoding()
    instance_symbol = self.INSTANCE_SYMBOLS.get(
        status, InstanceSymbol(best='?', alt='?')
    )

    return (
        self._PickSymbol(instance_symbol.best, instance_symbol.alt, encoding),
        instance_symbol.color,
    )

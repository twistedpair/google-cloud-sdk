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

"""Contains shared methods for printing k8s object in a human-readable way."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import textwrap

from googlecloudsdk.api_lib.run import container_resource
from googlecloudsdk.api_lib.run import k8s_object
from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.resource import custom_printer_base as cp


def OrderByKey(map_):
  for k in sorted(map_):
    yield k, (map_.get(k) if map_.get(k) is not None else '')


def FormatReadyMessage(record):
  """Returns the record's status condition Ready (or equivalent) message."""
  if record.ready_condition and record.ready_condition['message']:
    symbol, color = record.ReadySymbolAndColor()
    return console_attr.GetConsoleAttr().Colorize(
        textwrap.fill('{} {}'.format(
            symbol, record.ready_condition['message']), 100), color)
  elif record.status is None:
    return console_attr.GetConsoleAttr().Colorize(
        'Error getting status information', 'red')
  else:
    return ''


def LastUpdatedMessage(record):
  if record.status is None:
    return 'Unknown update information'
  modifier = record.last_modifier or '?'
  last_transition_time = '?'
  for condition in record.status.conditions:
    if condition.type == 'Ready' and condition.lastTransitionTime:
      last_transition_time = condition.lastTransitionTime
  return 'Last updated on {} by {}'.format(last_transition_time, modifier)


def GetLabels(labels):
  """Returns a human readable description of user provided labels if any."""
  if not labels:
    return ''
  return ' '.join(
      sorted([
          '{}:{}'.format(k, v)
          for k, v in labels.items()
          if not k.startswith(k8s_object.INTERNAL_GROUPS)
      ]))


def BuildHeader(record):
  con = console_attr.GetConsoleAttr()
  status = con.Colorize(*record.ReadySymbolAndColor())
  try:
    place = 'region ' + record.region
  except KeyError:
    place = 'namespace ' + record.namespace
  return con.Emphasize('{} {} {} in {}'.format(status, record.Kind(),
                                               record.name, place))


def GetCloudSqlInstances(record):
  instances = record.annotations.get(container_resource.CLOUDSQL_ANNOTATION, '')
  return instances.replace(',', ', ')


def GetVpcConnector(record):
  return cp.Labeled([
      ('Name',
       record.annotations.get(container_resource.VPC_ACCESS_ANNOTATION, '')),
      ('Egress',
       record.annotations.get(container_resource.EGRESS_SETTINGS_ANNOTATION,
                              ''))
  ])


def GetBinAuthzPolicy(record):
  return record.annotations.get(k8s_object.BINAUTHZ_POLICY_ANNOTATION, '')


def GetBinAuthzBreakglass(record):
  return record.annotations.get(k8s_object.BINAUTHZ_BREAKGLASS_ANNOTATION)


def GetDescription(record):
  return record.annotations.get(k8s_object.DESCRIPTION_ANNOTATION)


def GetExecutionEnvironment(record):
  return record.annotations.get(k8s_object.EXECUTION_ENVIRONMENT_ANNOTATION, '')

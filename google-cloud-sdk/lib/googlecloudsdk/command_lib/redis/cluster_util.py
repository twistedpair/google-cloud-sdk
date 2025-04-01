# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Flag utilities for `gcloud redis clusters`."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from apitools.base.py import encoding
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base


def ClusterRedisConfigArgType(value):
  return arg_parsers.ArgDict()(value)


def ClusterUpdateRedisConfigFlag():
  return base.Argument(
      '--update-redis-config',
      metavar='KEY=VALUE',
      type=ClusterRedisConfigArgType,
      action=arg_parsers.UpdateAction,
      help="""\
            A list of Redis Cluster config KEY=VALUE pairs to update. If a
            config parameter is already set, its value is modified; otherwise a
            new Redis config parameter is added.
            """,
  )


def ClusterRemoveRedisConfigFlag():
  return base.Argument(
      '--remove-redis-config',
      metavar='KEY',
      type=arg_parsers.ArgList(),
      action=arg_parsers.UpdateAction,
      help="""\
      A list of Redis Cluster config parameters to remove. Removing a non-existent
      config parameter is silently ignored.""",
  )


def AdditionalClusterUpdateArguments():
  return [ClusterUpdateRedisConfigFlag(), ClusterRemoveRedisConfigFlag()]


def PackageClusterRedisConfig(config, messages):
  return encoding.DictToAdditionalPropertyMessage(
      config, messages.Cluster.RedisConfigsValue, sort_items=True
  )


def ParseTimeOfDayAlpha(start_time):
  return ParseTimeOfDay(start_time, 'v1alpha1')


def ParseTimeOfDayBeta(start_time):
  return ParseTimeOfDay(start_time, 'v1beta1')


def ParseTimeOfDayGa(start_time):
  return ParseTimeOfDay(start_time, 'v1')


def ParseTimeOfDay(start_time, api_version):
  m = re.match(r'^(\d?\d):00$', start_time)
  if m:
    message = apis.GetMessagesModule('redis', api_version)
    hour = int(m.group(1))
    if hour <= 23 and hour >= 0:
      return message.TimeOfDay(hours=hour)
  raise arg_parsers.ArgumentTypeError(
      'Failed to parse time of day: {0}, expected format: HH:00.'.format(
          start_time
      )
  )

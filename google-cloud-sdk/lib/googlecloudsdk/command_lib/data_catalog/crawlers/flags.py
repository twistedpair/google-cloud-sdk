# -*- coding: utf-8 -*- #
# Copyright 2019 Google Inc. All Rights Reserved.
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
"""Additional flags for data-catalog crawler commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base


def AddCrawlerScopeAndSchedulingFlagsForCreate():
  """Python hook to add the arguments for scope and scheduling options.

  Returns:
    List consisting of the scope and scheduling arg groups.
  """
  scope_group = base.ArgumentGroup(
      help='Arguments to configure the crawler scope:',
      required=True)
  scope_group.AddArgument(GetCrawlScopeArg())
  scope_group.AddArgument(GetBucketArgForCreate())

  scheduling_group = base.ArgumentGroup(
      help='Arguments to configure the crawler run scheduling:',
      required=True)
  scheduling_group.AddArgument(GetRunOptionArg())
  scheduling_group.AddArgument(GetRunScheduleArg())

  return [scope_group, scheduling_group]


def GetCrawlScopeArg():
  choices = {
      'bucket': 'Directs the crawler to crawl specific buckets within the '
                'project that owns the crawler.',
      'project': 'Directs the crawler to crawl all the buckets of the project '
                 'that owns the crawler.',
      'organization': 'Directs the crawler to crawl all the buckets of the '
                      'projects in the organization that owns the crawler.'}
  return base.ChoiceArgument(
      '--crawl-scope',
      choices=choices,
      required=True,
      help_str='Scope of the crawler.')


def GetBucketArgForCreate():
  return base.Argument(
      '--buckets',
      type=arg_parsers.ArgList(),
      metavar='BUCKET',
      help='A list of buckets to crawl. This argument should be provided if '
           'and only if `--crawl-scope=BUCKET` was specified.')


def GetRunOptionArg():
  choices = {
      'manual': 'The crawler run will have to be triggered manually.',
      'scheduled': 'The crawler will run automatically on a schedule.'}
  return base.ChoiceArgument(
      '--run-option',
      choices=choices,
      required=True,
      help_str='Run option of the crawler.')


def GetRunScheduleArg():
  help_str = ('Schedule for the crawler run. This argument should be provided '
              'if and only if `--run-option=SCHEDULED` was specified.')
  return base.ChoiceArgument(
      '--run-schedule',
      choices=['daily', 'weekly'],
      help_str=help_str)

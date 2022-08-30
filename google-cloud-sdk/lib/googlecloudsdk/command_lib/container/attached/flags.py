# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Helpers for flags in commands working with Anthos Multi-Cloud on Attached."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


def AddPlatformVersion(parser, required=True):
  parser.add_argument(
      '--platform-version',
      required=required,
      help='Platform version to use for the cluster.')


def GetPlatformVersion(args):
  return getattr(args, 'platform_version', None)

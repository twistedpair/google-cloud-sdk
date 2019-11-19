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
"""Flags for serverless local development setup."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


def CommonFlags(parser):
  """Add common flags for local developement environments."""
  parser.add_argument(
      '--dockerfile',
      default='Dockerfile',
      help='The Dockerfile for the service image.')

  parser.add_argument(
      '--service-name', required=False, help='Name of the service.')

  parser.add_argument(
      '--image-name', required=False, help='Name for the built docker image.')

  parser.add_argument(
      '--build-context-directory',
      help='If set, use this as the context directory when building the '
      'container image. Otherwise, the directory of the Dockerfile will be '
      'used.')

  parser.add_argument(
      '--service-account',
      help='When connecting to Google Cloud Platform services, use a service '
      'account key.')

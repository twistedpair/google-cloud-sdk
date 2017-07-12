# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Functions for dealing with managed instances groups updates."""

from googlecloudsdk.calliope import arg_parsers


def AddAutohealingArgs(parser, health_check_group):
  """Adds autohealing-related commandline arguments to parser."""
  health_check_group.add_argument(
      '--http-health-check',
      help=('Specifies the HTTP health check object used for autohealing '
            'instances in this group.'))
  health_check_group.add_argument(
      '--https-health-check',
      help=('Specifies the HTTPS health check object used for autohealing '
            'instances in this group.'))
  parser.add_argument(
      '--initial-delay',
      type=arg_parsers.Duration(),
      help="""\
      Specifies the length of the period during which the instance is known to
      be initializing and should not be autohealed even if unhealthy.
      Valid units for this flag are ``s'' for seconds, ``m'' for minutes and
      ``h'' for hours. If no unit is specified, seconds is assumed. This value
      cannot be greater than 1 hour.
      """)

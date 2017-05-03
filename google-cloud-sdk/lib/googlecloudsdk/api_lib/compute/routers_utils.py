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
"""Common classes and functions for routers."""


from googlecloudsdk.api_lib.compute import utils


def AddCommonArgs(parser, for_update=False):
  """Adds common arguments for routers add-interface or update-interface."""

  operation = 'added'
  if for_update:
    operation = 'updated'

  parser.add_argument(
      '--interface-name',
      required=True,
      help='The name of the interface being {0}.'.format(operation))

  parser.add_argument(
      '--ip-address',
      type=utils.IPV4Argument,
      help='The link local address of the router for this interface.')

  parser.add_argument(
      '--mask-length',
      type=int,
      # TODO(b/36051080): better help
      help='The mask for network used for the server IP address.')

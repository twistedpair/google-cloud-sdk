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
"""Helper methods for constructing messages for the container CLI."""

from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.container import constants
from googlecloudsdk.command_lib.container import container_command_util


def AutoUpdateUpgradeRepairMessage(value, flag_name):
  """Messaging for when auto-upgrades or node auto-repairs.

  Args:
    value: bool, value that the flag takes.
    flag_name: str, the name of the flag. Must be either autoupgrade or
        autorepair

  Returns:
    the formatted message string.
  """
  action = 'enable' if value else 'disable'
  plural = flag_name + 's'
  link = 'node-management' if flag_name == 'autoupgrade' else 'node-auto-repair'
  return ('This will {0} the {1} feature for nodes. Please see\n'
          'https://cloud.google.com/kubernetes-engine/docs/'
          '{2} for more\n'
          'information on node {3}.\n').format(action, flag_name, link, plural)


def GetAPIMismatchingWarning(track):
  """Warning for using an API version that mismatches the release track."""
  if not container_command_util.GetUseV1APIProperty():
    # No message if v1 API is not forced.
    return None
  tmpl = constants.KUBERNETES_API_MISMATCH_WARNING_TEMPLATE
  if track == base.ReleaseTrack.ALPHA:
    return (tmpl.format(track='alpha', api='v1alpha1') + '\n' +
            constants.KUBERNETES_V1ALPHA1_API_WARNING)
  if track == base.ReleaseTrack.BETA:
    return tmpl.format(track='beta', api='v1beta1')
  return None

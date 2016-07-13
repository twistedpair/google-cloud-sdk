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
"""Module for wrangling bigtable command arguments."""


class ArgAdder(object):
  """A class for adding Bigtable command-line arguments."""

  def __init__(self, parser):
    self.parser = parser

  def AddAsync(self):
    self.parser.add_argument(
        '--async',
        help='Return immediately, without waiting for operation to complete.',
        action='store_true')
    return self

  def AddCluster(self, positional=True):
    help_text = 'ID of the cluster.'
    if positional:
      self.parser.add_argument('cluster', help=help_text)
    else:
      self.parser.add_argument('--cluster', help=help_text, required=True)
    return self

  def AddClusterNodes(self, in_instance=False):
    self.parser.add_argument('--cluster-num-nodes' if in_instance else
                             '--num-nodes',
                             help='Number of nodes to serve.',
                             required=True,
                             type=int)
    return self

  def AddClusterStorage(self, in_instance=False):
    self.parser.add_argument(
        '--cluster-storage-type' if in_instance else '--storage',
        choices=['HDD', 'SSD'],
        default='SSD',
        type=str.upper,
        help='Storage class for the cluster. Valid options are HDD or SSD.')
    return self

  def AddClusterZone(self, in_instance=False):
    self.parser.add_argument(
        '--cluster-zone' if in_instance else '--zone',
        help='ID of the zone where the cluster is located. As of this release '
        'supported zones are: asia-east1-b, us-central1-b, us-central1-c, '
        'europe-west1-c',
        required=True)
    return self

  def AddInstance(self, positional=True, required=True, multiple=False):
    """Add argument for instance ID to parser."""
    help_text = 'ID of the instance.'
    if positional:
      self.parser.add_argument('instance',
                               help=help_text,
                               nargs='+' if multiple else None)
    else:
      self.parser.add_argument('--instances' if multiple else '--instance',
                               help=help_text,
                               required=required,
                               nargs='+' if multiple else None)
    return self

  def AddInstanceDescription(self, required=False):
    self.parser.add_argument('--description',
                             help='Friendly name of the instance.',
                             required=required)
    return self

# Copyright 2015 Google Inc. All Rights Reserved.
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

"""A library that is used to support our commands."""

import re
import time

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import exceptions as sdk_ex
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import progress_tracker


def GetAdminClient():
  """Shortcut to get the latest Bigtable Admin client."""
  return apis.GetClientInstance('bigtableadmin', 'v2')


def GetAdminMessages():
  """Shortcut to get the latest Bigtable Admin messages."""
  return apis.GetMessagesModule('bigtableadmin', 'v2')


def AddClusterIdArgs(parser):
  """Adds --zone and --cluster args to the parser."""
  parser.add_argument(
      '--zone',
      help='ID of the zone where the cluster is located.',
      # TODO(b/36049937): specify list of zones or not? eg...
      # choices=['europe-west1-c', 'us-central1-b'],
      required=True)
  parser.add_argument(
      'cluster',
      help='Unique ID of the cluster.')


def AddClusterInfoArgs(parser):
  """Adds --name and --nodes args to the parser."""
  parser.add_argument(
      '--description',
      help='Friendly name of the cluster.',
      required=True)
  parser.add_argument(
      '--nodes',
      help='Number of Cloud Bigtable nodes to serve.',
      required=True,
      type=int)
  parser.add_argument(
      '--async',
      help='Return immediately, without waiting for operation to finish.',
      action='store_true')


def ProjectUrl():
  return '/'.join(['projects', properties.VALUES.core.project.Get()])


def ZoneUrl(args):
  return '/'.join([ProjectUrl(), 'zones', args.zone])


def LocationUrl(location):
  # TODO(b/36049938): deprecate when a location resource is available in the API
  return '/'.join([ProjectUrl(), 'locations', location])


def ClusterUrl(args):
  """Creates the canonical URL for a cluster resource."""
  return '/'.join([ZoneUrl(args), 'clusters', args.cluster])


def MakeCluster(args):
  """Creates a dict representing a Cluster proto from user-specified args."""
  cluster = {}
  if args.description:
    cluster['display_name'] = args.description
  if args.nodes:
    cluster['serve_nodes'] = args.nodes
  return cluster


def ExtractZoneAndCluster(cluster_id):
  m = re.match('projects/[^/]+/zones/([^/]+)/clusters/(.*)', cluster_id)
  return m.group(1), m.group(2)


def WaitForOp(context, op_id, text):
  cli = context['clusteradmin']
  msg = context['clusteradmin-msgs'].BigtableclusteradminOperationsGetRequest(
      name=op_id)
  with progress_tracker.ProgressTracker(text, autotick=False) as pt:
    while True:
      # TODO(b/36049792): set reasonable timeout with input from API team
      resp = cli.operations.Get(msg)
      if resp.error:
        raise sdk_ex.HttpException(resp.error.message)
      if resp.done:
        break
      pt.Tick()
      time.sleep(0.5)


def WaitForOpV2(operation, spinner_text):
  """Wait for a longrunning.Operation to complete, using the V2 API.

  Currently broken pending fix of b/29563942.

  Args:
    operation: a longrunning.Operation message.
    spinner_text: message text to display on the console.

  Returns:
    true if completed successfully, false if timed out
  """
  tick_freq = 1  # poll every second
  tick_limit = 600  # timeout after ten minutes
  cli = GetAdminClient()
  msg = GetAdminMessages().BigtableadminOperationsGetRequest(
      operationsId=operation.name[11:])
  with progress_tracker.ProgressTracker(spinner_text, autotick=False) as pt:
    while tick_limit > 0:
      resp = cli.operations.Get(msg)
      if resp.error:
        raise sdk_ex.HttpException(resp.error.message)
      if resp.done:
        break
      pt.Tick()
      tick_limit -= tick_freq
      time.sleep(tick_freq)
  return resp.done


def WaitForInstance(client, operation_ref, message):
  poller = waiter.CloudOperationPoller(
      client.projects_instances, client.operations)
  return waiter.WaitFor(poller, operation_ref, message)


def GetInstanceRef(instance):
  return resources.REGISTRY.Parse(
      instance,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection='bigtableadmin.projects.instances')

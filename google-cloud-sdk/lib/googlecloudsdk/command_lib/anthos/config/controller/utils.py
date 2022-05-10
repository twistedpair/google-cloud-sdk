# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Utils for Config Controller commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.container import api_adapter as container_api_adapter
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import log

NOT_RUNNING_MSG = ('Config Controller {0} is not running. '
                   'The kubernetes API may not be available.')


def SetLocation():
  """Sets default location to '-' for list command."""
  return '-'


def InstanceAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='name',
      help_text='The name of the Config Controller instance.')


def LocationAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      help_text=("The name of the Config Controller instance location. "
                 "Currently, only ``us-central1'', ``us-east1'', "
                 "``northamerica-northeast1'', ``europe-north1'', "
                 "``australia-southeast1'', and "
                 "``asia-northeast1'' are supported."))


def GetInstanceResourceSpec():
  return concepts.ResourceSpec(
      'krmapihosting.projects.locations.krmApiHosts',
      resource_name='instance',
      krmApiHostsId=InstanceAttributeConfig(),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False)


def AddInstanceResourceArg(parser):
  concept_parsers.ConceptParser.ForResource(
      'name',
      GetInstanceResourceSpec(),
      'The identifier for a Config Controller instance.',
      required=True).AddToParser(parser)


def GetGKECluster(name, location):
  """Fetches the information about the GKE cluster backing the Config Controller."""

  cluster_id = 'krmapihost-' + name
  location_id = location
  project = None

  gke_api = container_api_adapter.NewAPIAdapter('v1')
  log.status.Print('Fetching cluster endpoint and auth data.')
  cluster_ref = gke_api.ParseCluster(cluster_id, location_id, project)
  cluster = gke_api.GetCluster(cluster_ref)

  if not gke_api.IsRunning(cluster):
    log.warning(NOT_RUNNING_MSG.format(cluster_ref.clusterId))

  return cluster, cluster_ref

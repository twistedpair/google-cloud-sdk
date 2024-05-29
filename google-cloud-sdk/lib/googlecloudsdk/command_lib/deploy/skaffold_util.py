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
"""Helper methods to generate a skaffold file."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections

from googlecloudsdk.core import yaml


CLOUD_RUN_GENERATED_SKAFFOLD_TEMPLATE = """\
apiVersion: skaffold/v3alpha1
kind: Config
manifests:
  rawYaml:
  - {}
deploy:
  cloudrun: {{}}
  """


GKE_GENERATED_SKAFFOLD_TEMPLATE = """\
apiVersion: skaffold/v2beta28
kind: Config
deploy:
  kubectl:
    manifests:
      - {}
  """


def _GetUniqueProfiles(pipeline_obj):
  """Gets unique profiles from pipeline_obj."""
  profiles = set()
  for stage in pipeline_obj.serialPipeline.stages:
    for profile in stage.profiles:
      profiles.add(profile)
  return profiles


def _AddProfiles(skaffold, pipeline_obj):
  """Adds the profiles in the provided pipeline to the skaffold configuration."""
  profiles = _GetUniqueProfiles(pipeline_obj)

  if not profiles:
    return

  skaffold['profiles'] = []
  for profile in profiles:
    skaffold['profiles'].append(collections.OrderedDict([('name', profile)]))
  return


def CreateSkaffoldFileForManifest(pipeline_obj, manifest, template):
  """Creates skaffold file when a cloud run or GKE manifest is provided to the release create command.

  Args:
    pipeline_obj: A Delivery Pipeline object, the profiles in the Delivery
      Pipeline stages will be added to the skaffold file.
    manifest: The name of the manifest file.
    template: The skaffold.yaml template.

  Returns:
    skaffold yaml.
  """

  skaffold = yaml.load(
      template.format(manifest),
      round_trip=True,
  )

  _AddProfiles(skaffold, pipeline_obj)

  return skaffold


def CreateSkaffoldFileForRunContainer(
    target_to_target_properties, pipeline_obj
):
  """Creates skaffold file for target_ids in _TargetProperties object.

  Args:
    target_to_target_properties: A dict of target_id to _TargetProperties.
    pipeline_obj: Delivery Pipeline object.

  Returns:
    skaffold yaml.
  """
  skaffold = collections.OrderedDict()
  skaffold['apiVersion'] = 'skaffold/v3alpha1'
  skaffold['kind'] = 'Config'
  profiles = _GetUniqueProfiles(pipeline_obj)
  if profiles:
    skaffold['profiles'] = []

  for target_id, target_property in target_to_target_properties.items():
    skaffold['profiles'].append(
        collections.OrderedDict([
            ('name', target_property.profile),
            ('manifests', {'rawYaml': ['{}_manifest.yaml'.format(target_id)]}),
        ])
    )
    profiles.remove(target_property.profile)

  for profile in profiles:
    skaffold['profiles'].append(collections.OrderedDict([('name', profile)]))

  skaffold['deploy'] = {'cloudrun': {}}
  return skaffold

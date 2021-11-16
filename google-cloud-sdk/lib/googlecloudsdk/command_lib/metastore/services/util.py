# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Utilities for "gcloud metastore services" commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import xml.etree.cElementTree as element_tree

from googlecloudsdk.command_lib.metastore import parsers
from googlecloudsdk.core import properties


def GetTier():
  """Returns the value of the metastore/tier config property.

  Config properties can be overridden with command line flags. If the --tier
  flag was provided, this will return the value provided with the flag.
  """
  return properties.VALUES.metastore.tier.Get(required=True)


def LoadHiveMetatsoreConfigsFromXmlFile(file_arg):
  """Convert Input XML file into Hive metastore configurations."""
  hive_metastore_configs = {}
  root = element_tree.fromstring(file_arg)

  for prop in root.iter('property'):
    hive_metastore_configs[prop.find('name').text] = prop.find('value').text
  return hive_metastore_configs


def GenerateNetworkConfigFromSubnetList(unused_ref, args, req):
  """Generates the NetworkConfig message from the list of subnetworks.

  Args:
    args: The request arguments.
    req: A request with `service` field.

  Returns:
    A request with network configuration field if `consumer-subnetworks` is
    present in the arguments.
  """
  if args.consumer_subnetworks:
    req.service.networkConfig = {
        'consumers': [{
            'subnetwork': parsers.ParseSubnetwork(s, args.location)
        } for s in args.consumer_subnetworks]
    }
  return req


def _GenerateAdditionalProperties(values_dict):
  """Format values_dict into additionalProperties-style dict."""
  props = [{'key': k, 'value': v} for k, v in sorted(values_dict.items())]
  return {'additionalProperties': props}


def _GenerateUpdateMask(args):
  """Constructs updateMask for patch requests.

  Args:
    args: The parsed args namespace from CLI.

  Returns:
    String containing update mask for patch request.
  """
  hive_metastore_configs = 'hive_metastore_config.config_overrides'
  labels = 'labels'
  arg_name_to_field = {
      '--port':
          'port',
      '--tier':
          'tier',
      '--update-hive-metastore-configs-from-file':
          'hive_metastore_config.config_overrides',
      '--clear-hive-metastore-configs':
          hive_metastore_configs,
      '--clear-labels':
          labels,
      '--kerberos-principal':
          'hive_metastore_config.kerberos_config.principal',
      '--keytab':
          'hive_metastore_config.kerberos_config.keytab',
      '--krb5-config':
          'hive_metastore_config.kerberos_config.krb5_config_gcs_uri',
      '--maintenance-window-day':
          'maintenance_window',
      '--maintenance-window-hour':
          'maintenance_window',
      '--data-catalog-sync':
          'metadataIntegration.dataCatalogConfig.enabled',
      '--no-data-catalog-sync':
          'metadataIntegration.dataCatalogConfig.enabled',
  }

  update_mask = set()
  for arg_name in set(
      args.GetSpecifiedArgNames()).intersection(arg_name_to_field):
    update_mask.add(arg_name_to_field[arg_name])
  hive_metastore_configs_update_mask_prefix = hive_metastore_configs + '.'
  if hive_metastore_configs not in update_mask:
    if args.update_hive_metastore_configs:
      for key in args.update_hive_metastore_configs:
        update_mask.add(hive_metastore_configs_update_mask_prefix + key)
    if args.remove_hive_metastore_configs:
      for key in args.remove_hive_metastore_configs:
        update_mask.add(hive_metastore_configs_update_mask_prefix + key)

  labels_update_mask_prefix = labels + '.'
  if labels not in update_mask:
    if args.update_labels:
      for key in args.update_labels:
        update_mask.add(labels_update_mask_prefix + key)
    if args.remove_labels:
      for key in args.remove_labels:
        update_mask.add(labels_update_mask_prefix + key)
  return ','.join(sorted(update_mask))


def SetServiceRequestUpdateHiveMetastoreConfigs(unused_job_ref, args,
                                                update_service_req):
  """Modify the Service update request to update, remove, or clear Hive metastore configurations.

  Args:
    unused_ref: A resource ref to the parsed Service resource.
    args: The parsed args namespace from CLI.
    update_service_req: Created Update request for the API call.

  Returns:
    Modified request for the API call.
  """
  hive_metastore_configs = {}
  if args.update_hive_metastore_configs:
    hive_metastore_configs = args.update_hive_metastore_configs
  if args.update_hive_metastore_configs_from_file:
    hive_metastore_configs = LoadHiveMetatsoreConfigsFromXmlFile(
        args.update_hive_metastore_configs_from_file)
  update_service_req.service.hiveMetastoreConfig.configOverrides = _GenerateAdditionalProperties(
      hive_metastore_configs)
  return update_service_req


def UpdateServiceMaskHook(unused_ref, args, update_service_req):
  """Constructs updateMask for update requests of Dataproc Metastore services.

  Args:
    unused_ref: A resource ref to the parsed Service resource.
    args: The parsed args namespace from CLI.
    update_service_req: Created Update request for the API call.

  Returns:
    Modified request for the API call.
  """
  update_service_req.updateMask = _GenerateUpdateMask(args)
  return update_service_req

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
"""Manages fetching and caching universe descriptor JSON files.

Universe descriptor files contain a list of attributes which GCP
clients use to derive universe-specific information (mostly domain names) to
display authentication pages, help links, etc, and to be able to form
universe-specific project names. UniverseDescriptor acts as gcloud's
fetching and caching utility. These descriptors need to be cached in order to
avoid requesting the data from the bucket every time we need to reference the
descriptor data. The cache will be refreshed in the following scenarios:

- User upgrades their version of gcloud using `gcloud components update`.
- The user runs `gcloud config set universe_domain` with a new universe_domain

Users of should only use it to reference the cached descriptors and should not
implement their own calls to fetch / update the descriptors.
"""

import json
import os
import sqlite3
from typing import Any, Dict, Mapping, Set, TypedDict

from cloudsdk.google.protobuf import json_format
from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core.configurations import named_configs
from googlecloudsdk.core.configurations import properties_file
from googlecloudsdk.core.universe_descriptor.v1 import universe_descriptor_data_pb2
from googlecloudsdk.core.util import pkg_resources
import requests


DESCRIPTOR_DATA_FILE_NAME = 'universe-descriptor.json'
DESCRIPTOR_DATA_BUCKET_NAME = 'universe-descriptor-data'
DESCRIPTOR_DATA_BUCKET_BACKUP_NAME = 'universe-descriptor-data-backup'
CONFIG_CACHE_DESCRIPTOR_DATA_TABLE_NAME = (
    'hidden_gcloud_config_universe_descriptor_data_cache'
)


class UniverseDescriptorError(exceptions.Error):
  """An exception to be raised when a universe descriptor error occurs."""


class UniverseDescriptorFetchError(UniverseDescriptorError):
  """An exception to be raised when downloading a universe descriptor file fails."""

  def __init__(self, universe_domain: str, error: Exception):
    """Constructs a new exception.

    Args:
      universe_domain: The universe_domain used to fetch the descriptors.
      error: The Exception that caused the request to fail.
    """
    super(UniverseDescriptorFetchError, self).__init__(
        f'The provided universe domain [{universe_domain}] is invalid.'
        ' Please check that the core/universe_domain property set is valid.'
        f' Request exception: {str(error)}'
    )


class UniverseDescriptorDataError(UniverseDescriptorError):
  """An exception to be raised when the universe descriptor data is invalid."""

  def __init__(self, universe_domain: str, error: Exception):
    """Constructs a new exception.

    Args:
      universe_domain: The universe_domain used to fetch the descriptors.
      error: The Exception that caused the request to fail.
    """
    super(UniverseDescriptorDataError, self).__init__(
        'The fetched universe descriptor with universe domain'
        f' [{universe_domain}] has invalid data. Request'
        f' exception: {str(error)}'
    )


class UniverseDescriptorDataSQLiteError(UniverseDescriptorError, sqlite3.Error):
  """An exception raised when a SQLite error occurs querying a descriptor."""

  def __init__(self, universe_domain: str, error: sqlite3.Error):
    """Constructs a new exception.

    Args:
      universe_domain: The universe_domain used to fetch the descriptors.
      error: The SQLite error that occurred.
    """
    super(UniverseDescriptorDataSQLiteError, self).__init__(
        'A SQLite error occurred while querying the universe descriptor with'
        f' universe domain [{universe_domain}]. Request exception: {str(error)}'
    )


def _GetValidatedDescriptorData(
    descriptor_data: Mapping[str, Any], universe_domain: str
) -> universe_descriptor_data_pb2.UniverseDescriptorData:
  """Builds a validated descriptor message to ensure it has the expected keys.

  Args:
    descriptor_data: The descriptor data, as a mapping of proto JSON to
      validate.
    universe_domain: The universe domain to validate the descriptor data for.

  Raises:
    UniverseDescriptorDataError: The descriptor data did not have the
      expected data.

  Returns:
    The descriptor data message.
  """
  if (
      'universeDomain' not in descriptor_data
      or descriptor_data.get('universeDomain') != universe_domain
  ):
    raise UniverseDescriptorDataError(
        universe_domain,
        KeyError(
            f'Universe domain [{universe_domain}] does not match the universe'
            ' domain in the descriptor data'
            f' [{descriptor_data.get("universeDomain", "undefined")}]'
        ),
    )
  descriptor_proto_message = (
      universe_descriptor_data_pb2.UniverseDescriptorData()
  )
  try:
    return json_format.ParseDict(
        descriptor_data,
        descriptor_proto_message,
        ignore_unknown_fields=True,
    )
  except json_format.ParseError as e:
    raise UniverseDescriptorDataError('invalid', e) from None


def GetAllConfigUniverseDomains() -> Set[str]:
  """Gets all unique universe domains used by all configs.

  Depending on the gcloud configs a user may have created, different universe
  domain may have been used accross them. iterates through all of the configs
  and compiles down a set of unique universe domains.

  Returns:
    The set of unique universe domains
  """
  all_configs = named_configs.ConfigurationStore.AllConfigs()
  all_config_universe_domains = set()
  for _, user_config in sorted(all_configs.items()):
    props = properties.VALUES.AllValues(
        list_unset=True,
        include_hidden=True,
        properties_file=properties_file.PropertiesFile([user_config.file_path]),
        only_file_contents=True,
    )
    all_config_universe_domains.add(
        props['core'].get('universe_domain')
        or properties.VALUES.core.universe_domain.default
    )
  return all_config_universe_domains


class UniverseDescriptorMapping(TypedDict):
  """A mapping of universe domain to the universe descriptor data.

  Attributes:
    universe_domain: The universe domain of the descriptor.
    universe_descriptor_data: The universe descriptor data message.
  """

  universe_domain: str
  universe_descriptor_data: universe_descriptor_data_pb2.UniverseDescriptorData


_all_cached_universe_descriptors: UniverseDescriptorMapping = {}


class UniverseDescriptor:
  """Manages the universe descriptor file fetching and caches the retrieved JSON files."""

  def Get(
      self, universe_domain: str, fetch_if_not_cached: bool = True
  ) -> universe_descriptor_data_pb2.UniverseDescriptorData:
    """Gets the universe descriptor as a proto message from the config cache.

    Args:
      universe_domain: The universe domain to query the config cache table for.
      fetch_if_not_cached: Whether to fetch the descriptor if it is not cached.

    Returns:
      The universe descriptor message for the given universe_domain.
    """
    universal_descriptor_data = _all_cached_universe_descriptors.get(
        universe_domain
    )
    if universal_descriptor_data is not None:
      return universal_descriptor_data
    descriptor_json = self._GetJson(universe_domain, fetch_if_not_cached)
    descriptor_message = _GetValidatedDescriptorData(
        descriptor_json, universe_domain
    )
    return descriptor_message

  def _GetJson(
      self, universe_domain: str, fetch_if_not_cached: bool = True
  ) -> Dict[str, Any]:
    """Gets the universe descriptor JSON from the config cache.

    All descriptors which have been previously cached will be accessible
    through this method. If a descriptor is not cached already, it will attempt
    to fetch it. A sample descriptor JSON would look like:

    {
      "version": "v1",
      "universeDomain": "universe.goog",
      "universeShortName": "google-universe-testing-environment",
      "projectPrefix": "google-testing-environment",
      "authenticationDomain": "auth.cloud.universe.goog",
      "cloudWebDomain": "cloud.universe.goog",
    }

    Args:
      universe_domain: The universe domain to query the config cache for.
      fetch_if_not_cached: Whether to fetch the descriptor if it is not cached.

    Returns:
      The JSON object of the universe descriptor data for the given
      universe_domain. An example descriptor JSON file can seen in
      googlecloudsdk/core/universe_descriptor/default-universe-descriptor.json

    Raises:
      UniverseDescriptorDataSQLiteError: An error occurred while fetching the
      descriptor data from the config cache.
    """
    config_store = config.GetConfigStore(
        CONFIG_CACHE_DESCRIPTOR_DATA_TABLE_NAME
    )
    try:
      return config_store.GetJSON(universe_domain)
    except sqlite3.Error as e:
      if not fetch_if_not_cached:
        raise UniverseDescriptorDataSQLiteError(universe_domain, e) from e
    try:
      return self.UpdateDescriptorFromUniverseDomain(universe_domain)
    except sqlite3.Error as e:
      raise UniverseDescriptorDataSQLiteError(universe_domain, e) from e

  def UpdateAllDescriptors(self) -> None:
    """Refreshes all descriptors according to config universe domains."""
    all_config_universe_domains = GetAllConfigUniverseDomains()
    for config_universe_domain in sorted(all_config_universe_domains):
      try:
        self.UpdateDescriptorFromUniverseDomain(config_universe_domain)
      except (UniverseDescriptorFetchError, UniverseDescriptorDataError):
        pass

  def UpdateDescriptorFromUniverseDomain(
      self, universe_domain: str
  ) -> Mapping[str, Any]:
    """Refreshes a singular descriptor according to the universe domain given.

    Fetches the latest descriptor for a universe domain and stores it in the
    cache if the object exists.

    Args:
      universe_domain: The universe domain to update the dscriptor of.

    Returns:
      The universe descriptor message for the given universe_domain.
    """
    if universe_domain == properties.VALUES.core.universe_domain.default:
      descriptor_data = json.loads(
          pkg_resources.GetResource(
              __package__,
              'universe_descriptor/default-universe-descriptor.json',
          )
      )
    else:
      descriptor_data = self._GetDescriptorFileFromBucket(universe_domain)
    descriptor_data_message = _GetValidatedDescriptorData(
        descriptor_data, universe_domain
    )
    self._StoreInConfigCache(descriptor_data)
    self._AddToInMemoryCache(universe_domain, descriptor_data_message)
    return descriptor_data

  def DeleteDescriptorFromUniverseDomain(self, universe_domain: str) -> bool:
    """Deletes a descriptor in the config cache with the given universe domain.

    Args:
      universe_domain: The universe domain of the descriptor to delete in the
        config cache.

    Returns:
      True if the descriptor was successfully deleted, False otherwise.
    """
    config_store = config.GetConfigStore(
        CONFIG_CACHE_DESCRIPTOR_DATA_TABLE_NAME
    )
    try:
      config_store.Remove(universe_domain)
      self._RemoveFromInMemoryCache(universe_domain)
    except sqlite3.Error as e:
      raise UniverseDescriptorDataSQLiteError(universe_domain, e) from e
    return True

  def _AddToInMemoryCache(
      self,
      universe_domain: str,
      universe_descriptor_message: universe_descriptor_data_pb2.UniverseDescriptorData,
  ) -> None:
    """Adds a universe descriptor to the in-memory cache."""
    _all_cached_universe_descriptors[universe_domain] = (
        universe_descriptor_message
    )

  def _RemoveFromInMemoryCache(self, universe_domain: str) -> None:
    """Removes a universe descriptor from the in-memory cache."""
    if universe_domain in _all_cached_universe_descriptors:
      del _all_cached_universe_descriptors[universe_domain]

  def _StoreInConfigCache(self, descriptor_data: Dict[str, Any]):
    """Stores the descriptor data in the config cache.

    The config SQLite cache includes a table specifically for caching all the
    descriptor data a user may use. Since they can have multiple descriptors,
    the table is keyed by the universe_domain of the descriptor. Providing a
    descriptor dict which does not have this key will result in an error. If the
    key already exists in the table, the entire data blob will get overwritten
    to what was provided.

    Args:
      descriptor_data: The descriptor data to store in the SQLite table.

    Raises:
      UniverseDescriptorDataError: The provided descriptor data did not have
      the expected keys.
    """
    config_store = config.GetConfigStore(
        CONFIG_CACHE_DESCRIPTOR_DATA_TABLE_NAME
    )
    # User can have multiple descriptor dicts so we key by universe domain
    try:
      descriptor_data_universe_domain = descriptor_data['universeDomain']
    except KeyError as e:
      raise UniverseDescriptorDataError('undefined', e)
    try:
      config_store.Set(descriptor_data_universe_domain, descriptor_data)
    except sqlite3.Error as e:
      raise UniverseDescriptorDataSQLiteError(
          descriptor_data_universe_domain, e
      ) from e

  def _GetDescriptorFileFromBucket(
      self, universe_domain: str
  ) -> Dict[str, Any]:
    """Fetches the universe descriptor file from GCS.

    The GCS bucket is publicly readable and contains the
    universe-descriptor.json file to read. If for any reason the primary bucket
    read fails, the request will gracefully fallback and attempt to read from
    the backup bucket. If the backup also fails, an exception is raised.

    Args:
      universe_domain: The universe domain used to construct the request URI to.

    Returns:
      The universe descriptor data JSON dictionary.

    Raises:
      UniverseDescriptorFetchError: An error occurred fetching the descriptor.
    """
    descriptor_data_uri = (
        f'https://storage.{os.path.join(universe_domain, DESCRIPTOR_DATA_BUCKET_NAME, DESCRIPTOR_DATA_FILE_NAME)}'
    )
    try:
      try:
        response = requests.get(descriptor_data_uri)
      except requests.exceptions.RequestException:
        # Try backup bucket
        descriptor_data_uri = (
            f'https://storage.{os.path.join(universe_domain, DESCRIPTOR_DATA_BUCKET_BACKUP_NAME, DESCRIPTOR_DATA_FILE_NAME)}'
        )
        response = requests.get(descriptor_data_uri)
    except requests.exceptions.RequestException as e:
      raise UniverseDescriptorFetchError(universe_domain, e)
    return response.json()

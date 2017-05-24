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
"""Common utilities for the Cloud Datapol API."""

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources

_DATAPOL_API_NAME = 'datapol'
_DATAPOL_API_VERSION = 'v1alpha1'

# Temporary taxonomy store id holder.
_STORE_ID_PLACE_HOLDER = 111


def GetMessagesModule():
  return apis.GetMessagesModule(_DATAPOL_API_NAME, _DATAPOL_API_VERSION)


def GetClientInstance():
  return apis.GetClientInstance(_DATAPOL_API_NAME, _DATAPOL_API_VERSION)


def GetProjectName():
  """Gets name of the current project."""
  return properties.VALUES.core.project.Get(required=True)


def GetTaxonomyStoresId():
  """Gets id of current taxonomy store."""
  return _STORE_ID_PLACE_HOLDER


def GetTaxonomyRelativeName(taxonomy_name):
  """Gets the taxonomy resource name from a taxonomy name."""
  return resources.REGISTRY.Create(
      'datapol.taxonomyStores.dataTaxonomies',
      taxonomyStoresId=GetTaxonomyStoresId(),
      dataTaxonomiesId=taxonomy_name).RelativeName()


def GetAnnotationRelativeName(taxonomy_name, annotation_name):
  """Gets the annotation resource name from taxonomy and annotation name."""
  return resources.REGISTRY.Create(
      'datapol.taxonomyStores.dataTaxonomies.annotations',
      taxonomyStoresId=GetTaxonomyStoresId(),
      dataTaxonomiesId=taxonomy_name,
      annotationsId=annotation_name).RelativeName()


def ErrorWrapper(err, resource_name):
  """Wraps http errors to handle resources names with more than 4 '/'s.

  Args:
    err: An apitools.base.py.exceptions.HttpError.
    resource_name: The requested resource name.

  Returns:
    A googlecloudsdk.api_lib.util.exceptions.HttpException.
  """
  exc = exceptions.HttpException(err)
  if exc.payload.status_code == 404:
    # status_code specific error message
    exc.error_format = ('{{api_name}}: {resource_name} not found.').format(
        resource_name=resource_name)
  else:
    # override default error message
    exc.error_format = ('Unknown error. Status code {status_code}.')
  return exc

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

"""CLI implementation for datapol tag."""

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.datapol import tagging
from googlecloudsdk.api_lib.util import exceptions


def TagDataAsset(data_asset, annotation, load_from, remove):
  """Tag a data asset with annotation or remove existing annotation.

  Args:
    data_asset: list of data asset resource names.
    annotation: full annotation <taxonomy::annotation>.
    load_from: path to a file with (dataasset,annotation) pairs
    remove: if true, remove existing annotation instead.

  Raises:
    exceptions.HttpException: on unknown errors.

  Returns:
    It always returns 0 if no exceptions raised.
  """
  if load_from:
    # TODO(b/32858676): Implemented load from file.
    raise NotImplementedError()
  if remove:
    # TODO(b/32858676): Implement annotation removal.
    raise NotImplementedError()

  try:
    for data_asset_path in data_asset:
      tagging.Apply(data_asset_path, annotation)
  except apitools_exceptions.HttpError as e:
    exc = exceptions.HttpException(e)
    if exc.payload.status_code == 404:
      # status_code specific error message
      exc.error_format = '{api_name}: {resource_name} not found.'
    else:
      # override default error message
      exc.error_format = 'Unknown error. Status code {status_code}.'
    raise exc

  return 0

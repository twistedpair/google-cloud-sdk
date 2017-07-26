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

from googlecloudsdk.api_lib.datapol import tagging
from googlecloudsdk.api_lib.util import exceptions
from googlecloudsdk.core import exceptions as core_exceptions


class Error(core_exceptions.Error):
  pass


def TagDataAsset(data_asset, taxonomy_annotation, load_from, remove):
  """Tag a data asset with annotation or remove existing annotation.

  Args:
    data_asset: list of data asset resource names.
    taxonomy_annotation: full taxonomy and annotation <taxonomy::annotation>.
    load_from: path to a file with (dataasset,annotation) pairs
    remove: if true, remove existing annotation instead.

  Raises:
    Error: on taxonomy_annotation malformed or other unknown errors.

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
    taxonomy, annotation = taxonomy_annotation.split('::', 1)
  except ValueError:
    raise Error(
        'TAXONOMY_ANNOTATION should be in the format taxonomy::annotation')

  exc_list = []
  for data_asset_path in data_asset:
    try:
      tagging.Apply(data_asset_path, taxonomy, annotation)
    except exceptions.HttpException as e:
      exc_list.append('"{data_asset_path}": {err}'.format(
          data_asset_path=data_asset_path, err=e.message))

  if exc_list:
    raise Error('Apply tag failed on following data assets:\n' +
                '\n'.join(exc_list))

  return 0

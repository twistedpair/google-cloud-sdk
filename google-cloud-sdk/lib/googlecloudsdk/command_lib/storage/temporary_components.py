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
"""Utilities for getting temporary resources for composite uploads."""
# TODO(b/182259875): Merge this file with copy_component_util.py.

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


import hashlib

from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage.resources import resource_reference


_PARALLEL_UPLOAD_TEMPORARY_NAMESPACE = (
    '/gcloud/tmp/parallel_composite_uploads/'
    'see_gcloud_storage_cp_help_for_details/')


_PARALLEL_UPLOAD_STATIC_SALT = """
PARALLEL_UPLOAD_SALT_TO_PREVENT_COLLISIONS.
The theory is that no user will have prepended this to the front of
one of their object names and then do an MD5 hash of the name, and
then prepended PARALLEL_UPLOAD_TEMP_NAMESPACE to the front of their object
name. Note that there will be no problems with object name length since we
hash the original name.
"""


def _get_temporary_name(source_resource, component_id):
  """Gets a temporary object name for a component of source_resource."""
  source_name = source_resource.storage_url.object_name
  salted_name = _PARALLEL_UPLOAD_STATIC_SALT + source_name

  sha1_hash = hashlib.sha1(salted_name.encode('utf-8'))

  return '{}{}_{}'.format(
      _PARALLEL_UPLOAD_TEMPORARY_NAMESPACE,
      sha1_hash.hexdigest(),
      str(component_id))


def get_resource(source_resource, destination_resource, component_id):
  """Gets a temporary component destination resource for a composite upload.

  Args:
    source_resource (resource_reference.FileObjectResource): The upload source.
    destination_resource (resource_reference.ObjectResource|UnknownResource):
        The upload destination.
    component_id (int): An id that's not shared by any other component in this
        transfer.

  Returns:
    A resource_reference.UnknownResource representing the component's
    destination.
  """
  component_object_name = _get_temporary_name(source_resource, component_id)

  destination_url = destination_resource.storage_url
  component_url = storage_url.CloudUrl(
      destination_url.scheme,
      destination_url.bucket_name,
      component_object_name)

  return resource_reference.UnknownResource(component_url)

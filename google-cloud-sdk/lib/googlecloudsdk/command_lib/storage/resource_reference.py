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
"""Classes for cloud/file references yielded by storage iterators."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


class ResourceReference(object):
  """Base class for a reference to one fully expanded iterator result.

  This allows polymorphic iteration over wildcard-iterated URLs.  The
  reference contains a fully expanded URL string containing no wildcards and
  referring to exactly one entity (if a wildcard is contained, it is assumed
  this is part of the raw string and should never be treated as a wildcard).

  Each reference represents a Bucket, Object, or Prefix.  For filesystem URLs,
  Objects represent files and Prefixes represent directories.

  The root_object member contains the underlying object as it was retrieved.
  It is populated by the calling iterator, which may only request certain
  fields to reduce the number of server requests.

  For filesystem URLs, root_object is not populated.

  Attributes:
    storage_url (StorageUrl): A StorageUrl object representing the root_object
    root_object (apitools.messages.Object): None for filesystme url
    url_string (str): String representation of storage url.
      e.g "gs://mybucket/myobject"
  """

  def __init__(self, storage_url, root_object=None):
    self.storage_url = storage_url
    self.root_object = root_object
    self.url_string = storage_url.url_string

  def __str__(self):
    return self.url_string


class BucketReference(ResourceReference):
  """ResourceReference subclass for buckets."""


class PrefixReference(ResourceReference):
  """ResourceReference subclass for prefix.

  For filesystem, prefix represents directories
  """


class ObjectReference(ResourceReference):
  """ResourceReference subclass for objects.

  For filesystem, this class represents the file.
  """


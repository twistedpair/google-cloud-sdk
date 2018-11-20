# -*- coding: utf-8 -*- #
# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Utilities for expanding wildcarded GCS pathnames."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import fnmatch
import os
import re

from googlecloudsdk.api_lib.storage import storage_api
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.core import properties

import six


class PathExpander(six.with_metaclass(abc.ABCMeta)):
  """Abstract base class for path wildcard expansion."""

  EXPANSION_CHARS = '[*?[]'

  def __init__(self, sep):
    self._sep = sep

  @abc.abstractmethod
  def AbsPath(self, path):
    pass

  @abc.abstractmethod
  def IsDir(self, path):
    pass

  @abc.abstractmethod
  def Exists(self, path):
    pass

  @abc.abstractmethod
  def ListDir(self, path):
    pass

  @abc.abstractmethod
  def Join(self, path1, path2):
    pass

  def ExpandPath(self, path, include_directories=False):
    """Expand the given path that contains wildcard characters.

    Args:
      path: str, The path to expand.
      include_directories: bool, By default, only files that match the wildcard
        path are returned. If set to True, any directories that matches the
        wildcard will also be returned.

    Returns:
      {str}, The set of files and directories (if requested) that match the
      wildcard path. All returned paths are absolute.
    """
    return {p for p in self._Glob(self.AbsPath(path))
            if (include_directories or not p.endswith(self._sep))}

  def _HasExpansion(self, path):
    return bool(re.search(PathExpander.EXPANSION_CHARS, path))

  def _Glob(self, path):
    if not self._HasExpansion(path):
      if self.Exists(path):
        yield self._FormatPath(path)
      return

    dir_path, basename = os.path.split(path)
    has_basename_expansion = self._HasExpansion(basename)
    for expanded_dir_path in self._Glob(dir_path):
      if not has_basename_expansion:
        path = self.Join(expanded_dir_path, basename)
        if self.Exists(path):
          yield self._FormatPath(path)
      else:
        if basename == '**':
          for n in self._RecursiveDirList(expanded_dir_path):
            yield self._FormatPath(n)
        else:
          for n in fnmatch.filter(
              self.ListDir(expanded_dir_path),
              basename):
            yield self._FormatPath(self.Join(expanded_dir_path, n))

  def _RecursiveDirList(self, dir_path):
    for n in self.ListDir(dir_path):
      path = self.Join(dir_path, n)
      yield path
      for x in self._RecursiveDirList(path):
        yield x

  def _FormatPath(self, path):
    if self.IsDir(path) and not path.endswith(self._sep):
      path = path + self._sep
    return path


class LocalPathExpander(PathExpander):
  """Implements path expansion for the local filesystem."""

  def __init__(self):
    super(LocalPathExpander, self).__init__(os.sep)

  def AbsPath(self, path):
    return os.path.abspath(path)

  def IsDir(self, path):
    return os.path.isdir(path)

  def Exists(self, path):
    return os.path.exists(path)

  def ListDir(self, path):
    try:
      return os.listdir(path)
    except os.error:
      return []

  def Join(self, path1, path2):
    return os.path.join(path1, path2)


class GCSPathExpander(PathExpander):
  """Implements path expansion for gs:// formatted resource strings."""

  def __init__(self):
    super(GCSPathExpander, self).__init__('/')
    self._client = storage_api.StorageClient()
    self._objects = {}
    self._object_details = {}

  def GetObjectDetails(self, object_paths):
    return {p: self._object_details.get(p) for p in object_paths}

  def AbsPath(self, path):
    if not path.startswith('gs://'):
      raise ValueError('GCS paths must be absolute (starting with gs://)')
    return path

  def IsDir(self, path):
    exists, is_dir = self._Exists(path)
    return exists and is_dir

  def Exists(self, path):
    exists, _ = self._Exists(path)
    return exists

  def _Exists(self, path):
    if self._IsRoot(path):
      # Root of the filesystem always exists
      return True, True

    obj_ref = storage_util.ObjectReference.FromUrl(
        path, allow_empty_object=True)
    self._LoadObjectsIfMissing(obj_ref.bucket_ref)

    if obj_ref.bucket in self._objects:
      if not obj_ref.name:
        # Just a bucket, and it exists.
        return True, True
      if obj_ref.name in self._objects[obj_ref.bucket]:
        # This is an object and it exists.
        return True, False
      # See if this is a directory prefix of an existing object.
      dir_name = self._GetDirString(obj_ref.name)
      for i in self._objects[obj_ref.bucket]:
        if i.startswith(dir_name):
          return True, True

    return False, False

  def ListDir(self, path):
    if self._IsRoot(path):
      # The contents of the root filesystem are the buckets in the current
      # project.
      for b in self._client.ListBuckets(
          project=properties.VALUES.core.project.Get(required=True)):
        self._objects.setdefault(b.name, set())
        yield b.name
      return

    obj_ref = storage_util.ObjectReference.FromUrl(
        path, allow_empty_object=True)
    self._LoadObjectsIfMissing(obj_ref.bucket_ref)

    dir_name = self._GetDirString(obj_ref.name)
    parent_dir_length = len(dir_name)

    seen = set()
    for obj_name in self._objects[obj_ref.bucket]:
      if obj_name.startswith(dir_name):
        suffix = obj_name[parent_dir_length:]
        result = suffix.split(self._sep)[0]
        if result not in seen:
          seen.add(result)
          yield result

  def Join(self, path1, path2):
    if self._IsRoot(path1):
      return 'gs://' + path2.lstrip(self._sep)
    return path1.rstrip(self._sep) + self._sep + path2.lstrip(self._sep)

  def _IsRoot(self, path):
    return path == 'gs://' or path == 'gs:'

  def _LoadObjectsIfMissing(self, bucket_ref):
    objects = self._objects.get(bucket_ref.bucket)
    if not objects:
      # We may know that the bucket exists but not have listed objects yet, or
      # we may know nothing about the bucket.
      try:
        objects = self._client.ListBucket(bucket_ref)
        object_names = set()
        for o in objects:
          full_path = 'gs://' + self.Join(bucket_ref.bucket, o.name)
          self._object_details[full_path] = o
          object_names.add(o.name)
        # Only try to set the result after we start iterating because the API
        # call is not actually made until you try to consume the results. If
        # an API error occurs (like the bucket doesn't exist) we don't want
        # to accidentally cache that it was found.
        self._objects.setdefault(bucket_ref.bucket, set()).update(object_names)
      except storage_api.BucketNotFoundError:
        pass

  def _GetDirString(self, path):
    if path and not path.endswith(self._sep):
      return path + self._sep
    return path

  def _FormatPath(self, path):
    path = super(GCSPathExpander, self)._FormatPath(path)
    return 'gs://' if path == 'gs:/' else path

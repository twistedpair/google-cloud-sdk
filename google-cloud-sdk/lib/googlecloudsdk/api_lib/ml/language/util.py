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
"""Utilities for gcloud ml language commands."""

from googlecloudsdk.api_lib.ml import content_source
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.core import exceptions

LANGUAGE_API = 'language'


class Error(exceptions.Error):
  """Exceptions for this module."""


class ContentFileError(Error):
  """Error if content file can't be read and isn't a GCS URL."""


class ContentError(Error):
  """Error if content is not given."""


def GetContentSource(content=None, content_file=None):
  """Builds a ContentSource object from information about the content source.

  If content_file is given and appears to be a Google Cloud Storage URL,
  this URL is given in the Document message. If content_file is a local
  path, the file is read and the Document message contains its raw contents.
  A ContentFileError is raised if the file can't be found.

  If instead content is given, the Document message contains the content
  or raises a ContentError if it is empty.

  Args:
    content: str, the text to be analyzed.
    content_file: str, the file to be used to analyze text.

  Raises:
    ValueError: if content and content_file are both given.
    ContentFileError: if content file can't be found and is not a GCS URL.
    ContentError: if content is given but empty.

  Returns:
    ContentSource: an object containing information about the content
        to be sent to the Natural Language API.
  """
  if content_file:
    if content:
      raise ValueError('Either a file or content must be provided for '
                       'analysis by the Natural Language API, not both.')
    try:
      return content_source.ContentSource.FromContentPath(
          content_file, LANGUAGE_API,
          url_validator=storage_util.ObjectReference.IsStorageUrl,
          read_mode='r')
    except content_source.UnrecognizedContentSourceError:
      raise ContentFileError('Could not find --content-file [{}]. '
                             'Content file must be a path to a local file or '
                             'a Google Cloud Storage URL (format: '
                             '`gs://bucket_name/object_name`)'.format(
                                 content_file))
  elif content:
    return content_source.LocalSource.FromContents(content, LANGUAGE_API)
  # Either content_file or content are required. If content is an empty
  # string, raise an error.
  raise ContentError('The content provided is empty. Please provide '
                     'language content to analyze.')


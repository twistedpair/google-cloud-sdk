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

import os

from apitools.base.py import encoding
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import exceptions

LANGUAGE_API = 'language'
LANGUAGE_API_VERSION = 'v1'


class Error(exceptions.Error):
  """Exceptions for this module."""


class ContentFileError(Error):
  """Error if content file can't be read and isn't a GCS URL."""


class ContentError(Error):
  """Error if content is not given."""


def GetLanguageClient(version=LANGUAGE_API_VERSION):
  return apis.GetClientInstance(LANGUAGE_API, version)


def GetLanguageMessages(version=LANGUAGE_API_VERSION):
  return apis.GetMessagesModule(LANGUAGE_API, version)


class LanguageClient(object):
  """Wrapper for the Cloud Language API client class."""

  def __init__(self, version=None):
    version = version or LANGUAGE_API_VERSION
    self.client = GetLanguageClient(version=version)
    self.messages = GetLanguageMessages(version=version)

  def _GetDocument(self, content_source=None, language=None,
                   content_type='PLAIN_TEXT'):
    """Builds a Document message from information about the document.

    Uses content_source to update the Document message. language and
    content_type are also added to message if not None.

    Args:
      content_source: ContentSource, the source for the document content.
      language: str, the language of the input text, if any.
      content_type: str, the format of the input text, if any.

    Returns:
      messages.Document: a document containing information for the API on what
          to analyze.
    """
    document = self.messages.Document(language=language)
    content_source.UpdateDocument(document)
    document.type = self.messages.Document.TypeValueValuesEnum(content_type)
    return document

  def _GetAnnotateRequest(self, feature, content_source, language=None,
                          content_type=None, encoding_type=None):
    """Builds an annotation request message.

    Args:
      feature: str, the name of the feature to request (e.g. 'extractEntities').
      content_source: ContentSource, the source for the content to be
          analyzed.
      language: str, the language of the input text.
      content_type: str, the format of the input text - 'PLAIN_TEXT' or 'HTML'.
      encoding_type: str, the encoding type to be used for calculating word
          offsets - 'UTF8', 'UTF16', 'UTF32', or 'NONE'.

    Raises:
      ValueError: if content and content_file are both given.
      ContentFileError: if content file can't be found and is not a GCS URL.
      ContentError: if content is given but empty.

    Returns:
      messages.AnnotateTextRequest: a request to be sent to the API.
    """
    document = self._GetDocument(content_source=content_source,
                                 language=language, content_type=content_type)
    msgs = self.messages  # Shorten for convenience/line length.
    encoding_enum = msgs.AnnotateTextRequest.EncodingTypeValueValuesEnum
    request = msgs.AnnotateTextRequest(
        document=document,
        features=encoding.PyValueToMessage(
            msgs.Features,
            {feature: True}
        )
    )
    if encoding_type:
      request.encodingType = encoding_enum(encoding_type)
    return request

  def Annotate(self, feature, content_source=None, language=None,
               content_type='PLAIN_TEXT', encoding_type=None):
    """Sends the annotate text request to the Language API.

    Args:
      feature: str, the name of the feature to request (e.g. 'extractEntities').
      content_source: ContentSource, the source for the content to be
          analyzed.
      language: str, the language of the input text.
      content_type: str, the format of the input text - 'PLAIN_TEXT' or 'HTML'.
      encoding_type: str, the encoding type to be used for calculating word
          offsets - 'UTF8', 'UTF16', 'UTF32', or 'NONE'.

    Raises:
      googlecloudsdk.api_lib.util.exceptions.HttpException: if the API returns
          an error.

    Returns:
      messages.AnnotateTextResponse: the response from the API.
    """
    request = self._GetAnnotateRequest(feature, content_source=content_source,
                                       language=language,
                                       content_type=content_type,
                                       encoding_type=encoding_type)
    return self.client.documents.AnnotateText(request)


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
    if storage_util.ObjectReference.IsStorageUrl(content_file):
      return StorageContentSource(content_file)
    elif os.path.isfile(content_file):
      with open(content_file) as open_file:
        return TextContentSource(open_file.read())
    else:
      raise ContentFileError('Could not find --content-file [{}]. '
                             'Content file must be a path to a local file or '
                             'a Google Cloud Storage URL (format: '
                             '`gs://bucket_name/object_name`)'.format(
                                 content_file))
  elif content:
    return TextContentSource(content)
  # Either content_file or content are required. If content is an empty
  # string, raise an error.
  raise ContentError('The content provided is empty. Please provide '
                     'language content to analyze.')


class ContentSource(object):
  """Small class to contain information about the source content to analyze."""

  def UpdateDocument(self):
    raise NotImplementedError


class StorageContentSource(object):
  """Class that represents content coming from a Google Cloud Storage object."""

  def __init__(self, content_uri):
    self.content_uri = content_uri

  def UpdateDocument(self, message):
    message.gcsContentUri = self.content_uri


class TextContentSource(object):
  """Class that represents content to be sent in full to Natural Language API.
  """

  def __init__(self, content):
    self.content = content

  def UpdateDocument(self, message):
    message.content = self.content

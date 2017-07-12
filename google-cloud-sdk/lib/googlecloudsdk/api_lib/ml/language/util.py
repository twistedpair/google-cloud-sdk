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
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import exceptions

LANGUAGE_API = 'language'
LANGUAGE_GA_VERSION = 'v1'
LANGUAGE_BETA_VERSION = 'v1beta2'


class Error(exceptions.Error):
  """Exceptions for this module."""


class ContentFileError(Error):
  """Error if content file can't be read and isn't a GCS URL."""


class ContentError(Error):
  """Error if content is not given."""


def GetLanguageClient(version=LANGUAGE_GA_VERSION):
  return apis.GetClientInstance(LANGUAGE_API, version)


def GetLanguageMessages(version=LANGUAGE_GA_VERSION):
  return apis.GetMessagesModule(LANGUAGE_API, version)


class LanguageClient(object):
  """Wrapper for the Cloud Language API client class."""

  def __init__(self, version=None, entity_sentiment_enabled=False):
    version = version or LANGUAGE_GA_VERSION
    self.client = GetLanguageClient(version=version)
    self.messages = GetLanguageMessages(version=version)
    self.features = {
        'analyzeEntities': (self.messages.AnalyzeEntitiesRequest,
                            self.client.documents.AnalyzeEntities),
        'analyzeSyntax': (self.messages.AnalyzeSyntaxRequest,
                          self.client.documents.AnalyzeSyntax),
        'analyzeSentiment': (self.messages.AnalyzeSentimentRequest,
                             self.client.documents.AnalyzeSentiment)
    }
    # analyzeEntitySentiment is only available in the beta API.
    if entity_sentiment_enabled:
      self.features.update({
          'analyzeEntitySentiment': (
              self.messages.AnalyzeEntitySentimentRequest,
              self.client.documents.AnalyzeEntitySentiment)})

  def _GetDocument(self, source=None, language=None,
                   content_type='PLAIN_TEXT'):
    """Builds a Document message from information about the document.

    Uses source to update the Document message. language and
    content_type are also added to message if not None.

    Args:
      source: content_source.ContentSource, the source for the document content.
      language: str, the language of the input text, if any.
      content_type: str, the format of the input text, if any.

    Returns:
      messages.Document: a document containing information for the API on what
          to analyze.
    """
    document = self.messages.Document(language=language)
    source.UpdateContent(document)
    document.type = self.messages.Document.TypeValueValuesEnum(content_type)
    return document

  def _GetAnnotateRequest(self, request_type, source, language=None,
                          content_type=None, encoding_type=None):
    """Builds an annotation request message.

    Args:
      request_type: the request type of the message to build (e.g.
          language_v1_messages.AnalyzeSentimentRequest).
      source: content_source.ContentSource, the source for the content to be
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
      (request_type) a request to be sent to the API, of the given type
    """
    document = self._GetDocument(source=source, language=language,
                                 content_type=content_type)
    encoding_enum = request_type.EncodingTypeValueValuesEnum
    request = request_type(document=document)
    if encoding_type:
      request.encodingType = encoding_enum(encoding_type)
    return request

  def SingleFeatureAnnotate(self, feature, source=None, language=None,
                            content_type='PLAIN_TEXT', encoding_type=None):
    """Builds and sends a request to the Language API to analyze text.

    Args:
      feature: str, the name of the feature (e.g. 'analyzeEntities').
      source: content_source.ContentSource, the source for the content to be
          analyzed.
      language: str, the language of the input text.
      content_type: str, the format of the input text - 'PLAIN_TEXT' or 'HTML'.
      encoding_type: str, the encoding type to be used for calculating word
          offsets - 'UTF8', 'UTF16', 'UTF32', or 'NONE'.

    Raises:
      googlecloudsdk.api_lib.util.exceptions.HttpException: if the API returns
          an error.
      NotImplementedError: if a feature is requested that isn't in the client.

    Returns:
      the response from the API (type depends on feature, for example
          if feature is analyzeEntities, response would be
          messages.AnalyzeEntitiesResponse).
    """
    request_type, method = self.features.get(feature, (None, None))
    if not (request_type and method):
      raise NotImplementedError('{} not supported by this client.'.format(
          feature))
    request = self._GetAnnotateRequest(request_type, source=source,
                                       language=language,
                                       content_type=content_type,
                                       encoding_type=encoding_type)
    return method(request)


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


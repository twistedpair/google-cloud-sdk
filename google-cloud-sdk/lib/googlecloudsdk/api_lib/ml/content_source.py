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
"""Small class to handle local and remote content sources for ml APIs."""
import abc
import os

from googlecloudsdk.core import exceptions


_LOCAL = 'local'
_REMOTE = 'remote'
# New APIs using this class need to be registered here.
_API_MESSAGE_FIELD_LOOKUP = {
    'speech': {
        _LOCAL: 'content',
        _REMOTE: 'uri'},
    'language': {
        _LOCAL: 'content',
        _REMOTE: 'gcsContentUri'},
    'videointelligence': {
        _LOCAL: 'inputContent',
        _REMOTE: 'inputUri'}
    }


class UnrecognizedContentSourceError(exceptions.Error):
  """Raised if given path is not local and doesn't match validator."""


class ContentError(exceptions.Error):
  """Raised if no data is found in local source."""


class MessageError(exceptions.Error):
  """Raised if the API is not registered in the message field lookup."""


class ContentSource(object):
  """Interface for interacting with content sources for ML APIs.

  This construct stores information about the content of data to be analyzed,
  such as text content (for Cloud Language) and audio content (for Cloud
  Speech). It is responsible for updating the correct field of the message
  representing the content.
  """
  __metaclass__ = abc.ABCMeta

  @staticmethod
  def GetFieldName(api_name, content_type):
    """Gets name of message field to update for the API/content type.

    Args:
      api_name: str, the name of the API.
      content_type: str, the type of content ('local' or 'remote').

    Raises:
      MessageError: if the API name or content type isn't registered with
          ContentSource.

    Returns:
      str, the name of the message field to be updated.
    """
    field_name = _API_MESSAGE_FIELD_LOOKUP.get(api_name, {}).get(content_type)
    if not field_name:
      raise MessageError('Could not find message information for [{}] API '
                         '[{}] content source.'.format(api_name, content_type))
    return field_name

  @staticmethod
  def FromContentPath(content_path, api_name, url_validator=None,
                      read_mode='rb', encode=None):
    """Creates a ContentSource object.

    Determines whether the source is local or a valid remote URL and creates
    a ContentSource object of the correct type.

    Args:
      content_path: str, the path to the content.
      api_name: str, the name of the API to use to look up message field names
          corresponding to local or remote sources.
      url_validator: function to validate URLs. If None, any path that doesn't
          exist locally is assumed to be a valid URL.
      read_mode: str, the mode to open the local source if applicable.
      encode: callable function to encode contents if needed.

    Raises:
      UnrecognizedContentSourceError: if the URL is invalid or the
          local path is not a file.
      MessageError: if the message field is not present.

    Returns:
      ContentSource, the created object.
    """
    # It's assumed that if the path is local, the user wants to upload
    # the data from the local file directly.
    if os.path.isfile(content_path):
      return LocalSource(content_path,
                         ContentSource.GetFieldName(api_name, _LOCAL),
                         read_mode=read_mode,
                         encode=encode)
    # If the URL is valid, create RemoteSource.
    elif url_validator and url_validator(content_path):
      return RemoteSource(content_path,
                          ContentSource.GetFieldName(api_name, _REMOTE))
    # If no URL validator is given and the path is not a known local path.
    elif not (url_validator or os.path.exists(content_path)):
      return RemoteSource(content_path,
                          ContentSource.GetFieldName(api_name, _REMOTE))
    # If we got here, either the URL is invalid or the path exists but
    # is not a file.
    raise UnrecognizedContentSourceError

  @abc.abstractmethod
  def UpdateContent(self, message):
    """Updates the given message with information about the data to be analyzed.

    Args:
      message: any API message class representing data, such as
          speech_v1_messages.RecognitionAudio.
    """
    raise NotImplementedError


class LocalSource(ContentSource):
  """Class to represent content on the user's local drive or in memory.

  LocalSource updates the message with the direct contents of the
  data to be analyzed.
  """

  def __init__(self, content_path, message_field, read_mode='rb',
               contents=None, encode=None):
    self.local_path = content_path
    self.read_mode = read_mode
    self.message_field = message_field
    self.contents = contents
    self.encode = encode

  @staticmethod
  def FromContents(contents, api_name):
    """Creates a ContentSource object.

    Creates a LocalSource object to store the data to be analyzed.

    Args:
      contents: the contents to be passed to the API.
      api_name: str, the name of the API whose messages will be used.

    Returns:
      ContentSource, the created object.
    """
    return LocalSource(None, ContentSource.GetFieldName(api_name, _LOCAL),
                       contents=contents)

  def UpdateContent(self, message):
    if self.local_path:
      with open(self.local_path, self.read_mode) as content_file:
        contents = content_file.read()
    else:
      contents = self.contents
    if not contents:
      raise ContentError(
          'No content found for field [{}]'.format(self.message_field))
    if self.encode:
      contents = self.encode(contents)
    setattr(message, self.message_field, contents)

  def __eq__(self, other):
    return (isinstance(other, LocalSource)
            and self.local_path == other.local_path
            and self.read_mode == other.read_mode
            and self.message_field == other.message_field
            and self.contents == other.contents)


class RemoteSource(ContentSource):
  """Class to represent content that is remote.

  RemoteSource updates the message with the URL representing the location
  of the data.
  """

  def __init__(self, content_path, message_field):
    self.remote_path = content_path
    self.message_field = message_field

  def UpdateContent(self, message):
    setattr(message, self.message_field, self.remote_path)

  def __eq__(self, other):
    return (isinstance(other, RemoteSource)
            and self.remote_path == other.remote_path
            and self.message_field == other.message_field)

# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Utilities for Cloud Pub/Sub Message Transforms API."""

from googlecloudsdk.api_lib.pubsub import utils
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import exceptions


class EmptyMessageException(exceptions.Error):
  """Error when no message was specified for a Test operation."""


class EmptyFilePathException(exceptions.Error):
  """Error when no message transforms file was specified for a Validate operation."""


def GetClientInstance(no_http=False):
  return apis.GetClientInstance('pubsub', 'v1', no_http=no_http)


def GetMessagesModule(client=None):
  client = client or GetClientInstance()
  return client.MESSAGES_MODULE


class MessageTransformsClient(object):
  """Client for message transforms service in the Cloud Pub/Sub API."""

  def __init__(self, client=None, messages=None):
    self.client = client or GetClientInstance()
    self.messages = messages or GetMessagesModule(client)
    self._service = self.client.projects

  def Validate(self, project_ref, message_transform_file=None):
    """Validates a message transform.

    Args:
      project_ref (Resource): Resource reference for the project.
      message_transform_file (str): The file path to the JSON or YAML file
        containing the message transform.

    Returns:
      ValidateMessageTransformResponse (success) if the message transform is
      valid, otherwise an error.

    Raises:
      EmptyFilePathException: If no message transform file was specified.
    """
    if not message_transform_file:
      raise EmptyFilePathException(
          'You need to specify a path to JSON or YAML file containing the'
          ' message transform to validate.'
      )

    try:
      message_transform = utils.GetMessageTransformFromFileForValidation(
          self.messages.MessageTransform, message_transform_file
      )
    except (
        utils.MessageTransformsInvalidFormatError,
        utils.MessageTransformsEmptyFileError,
        utils.MessageTransformsMissingFileError,
    ) as e:
      e.args = (utils.GetErrorMessage(e),)
      raise
    validate_request = self.messages.PubsubProjectsValidateMessageTransformRequest(
        project=project_ref.RelativeName(),
        validateMessageTransformRequest=self.messages.ValidateMessageTransformRequest(
            messageTransform=message_transform,
        ),
    )
    return self._service.ValidateMessageTransform(validate_request)

  def Test(
      self,
      project_ref,
      message_body=None,
      attributes=None,
      message_transforms_file=None,
      topic_ref=None,
      subscription_ref=None,
  ):
    """Tests applying message transforms to a message.

    Args:
      project_ref (Resource): Resource reference for the project.
      message_body (bytes): The message to test.
      attributes (list[AdditionalProperty]): List of attributes to attach to the
        message.
      message_transforms_file (str): The file path to the JSON or YAML file
        containing the message transforms.
      topic_ref (Resource): The topic containing the message transforms to test
        against.
      subscription_ref (Resource): The subscription containing the message
        transforms to test against.

    Returns:
      TestMessageTransformsResponse which contains a list of TransformedMessage.

    Raises:
      EmptyMessageException: If no message body or attributes were specified.
      EmptyMessageTransformsException: If no message
      transforms file/topic/subscription were specified.
    """
    if not message_body and not attributes:
      raise EmptyMessageException(
          'You cannot send an empty message. You must specify either a '
          'MESSAGE, one or more ATTRIBUTE, or both.'
      )

    message = self.messages.PubsubMessage(
        data=message_body,
        attributes=self.messages.PubsubMessage.AttributesValue(
            additionalProperties=attributes
        ),
    )
    message_transforms = None
    if message_transforms_file:
      try:
        message_transforms = utils.GetMessageTransformsFromFile(
            self.messages.MessageTransform,
            message_transforms_file,
            enable_vertex_ai_smt=False,
        )
      except (
          utils.MessageTransformsInvalidFormatError,
          utils.MessageTransformsEmptyFileError,
          utils.MessageTransformsMissingFileError,
      ) as e:
        e.args = (utils.GetErrorMessage(e),)
        raise

    message_transforms_msg = (
        self.messages.MessageTransforms(messageTransforms=message_transforms)
        if message_transforms
        else None
    )

    test_request = self.messages.PubsubProjectsTestMessageTransformsRequest(
        project=project_ref.RelativeName(),
        testMessageTransformsRequest=self.messages.TestMessageTransformsRequest(
            message=message,
            messageTransforms=message_transforms_msg,
            topic=topic_ref.RelativeName() if topic_ref else None,
            subscription=subscription_ref.RelativeName()
            if subscription_ref
            else None,
        ),
    )
    return self._service.TestMessageTransforms(test_request)

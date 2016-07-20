# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Manipulation of Bigquery API messages representing JSON values.
"""

from apitools.base.py import exceptions
from apitools.base.py import extra_types
from apitools.base.py import util

from googlecloudsdk.api_lib.bigquery import bigquery


class MessageBuilder(object):
  """Provides a method that builds a Bigquery JsonObject message from JSON text.

  The module defining Bigquery API messages is passed as an argument to the
  constructor.
  """

  def __init__(self, bigquery_messages):
    self._bigquery_messages = bigquery_messages

  def Build(self, json_text):
    """Builds a Bigquery JsonObject message from JSON text.

    Args:
      json_text: the JSON text, expected to represent an object
    Returns:
      The message in the Bigquery API messages module representing that object.
    Raises:
      bigquery.ClientError if the JSON text is not the valid
        representation of a JSON object
    """
    try:
      json_proto = extra_types.JsonProtoDecoder(json_text)
      util.Typecheck(
          json_proto, extra_types.JsonObject, 'JSON value is not an object.')
    except ValueError as e:
      raise bigquery.ClientError(str(e))
    except exceptions.TypecheckError as e:
      raise bigquery.ClientError(str(e))
    except exceptions.InvalidDataError as e:
      raise bigquery.ClientError(str(e))
    # Convert the top-level extra_types.JsonObject into a
    # self._bigquery_messages.JsonObject. This is a shallow conversion: Both
    # JsonObject classes represent their property values as
    # extra_types.JsonValue objects.
    bigquery_properties = [
        self._bigquery_messages.JsonObject.AdditionalProperty(
            key=proto_property.key, value=proto_property.value)
        for proto_property in json_proto.properties]
    return self._bigquery_messages.JsonObject(
        additionalProperties=bigquery_properties)

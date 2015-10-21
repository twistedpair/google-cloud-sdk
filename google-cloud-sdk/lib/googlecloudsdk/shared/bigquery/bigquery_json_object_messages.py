# Copyright 2015 Google Inc. All Rights Reserved.

"""Manipulation of Bigquery API messages representing JSON values.
"""

from googlecloudsdk.shared.bigquery import bigquery
from googlecloudsdk.third_party.apitools.base.py import exceptions
from googlecloudsdk.third_party.apitools.base.py import extra_types
from googlecloudsdk.third_party.apitools.base.py import util


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

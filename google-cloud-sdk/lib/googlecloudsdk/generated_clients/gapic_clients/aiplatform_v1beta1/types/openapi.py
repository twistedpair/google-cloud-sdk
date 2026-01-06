# -*- coding: utf-8 -*-
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from __future__ import annotations

from typing import MutableMapping, MutableSequence

import proto  # type: ignore

from cloudsdk.google.protobuf import struct_pb2  # type: ignore


__protobuf__ = proto.module(
    package='google.cloud.aiplatform.v1beta1',
    manifest={
        'Type',
        'Schema',
    },
)


class Type(proto.Enum):
    r"""Type contains the list of OpenAPI data types as defined by
    https://swagger.io/docs/specification/data-models/data-types/

    Values:
        TYPE_UNSPECIFIED (0):
            Not specified, should not be used.
        STRING (1):
            OpenAPI string type
        NUMBER (2):
            OpenAPI number type
        INTEGER (3):
            OpenAPI integer type
        BOOLEAN (4):
            OpenAPI boolean type
        ARRAY (5):
            OpenAPI array type
        OBJECT (6):
            OpenAPI object type
        NULL (7):
            Null type
    """
    TYPE_UNSPECIFIED = 0
    STRING = 1
    NUMBER = 2
    INTEGER = 3
    BOOLEAN = 4
    ARRAY = 5
    OBJECT = 6
    NULL = 7


class Schema(proto.Message):
    r"""Defines the schema of input and output data. This is a subset of the
    `OpenAPI 3.0 Schema
    Object <https://spec.openapis.org/oas/v3.0.3#schema-object>`__.

    Attributes:
        type_ (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.Type):
            Optional. Data type of the schema field.
        format_ (str):
            Optional. The format of the data. For ``NUMBER`` type,
            format can be ``float`` or ``double``. For ``INTEGER`` type,
            format can be ``int32`` or ``int64``. For ``STRING`` type,
            format can be ``email``, ``byte``, ``date``, ``date-time``,
            ``password``, and other formats to further refine the data
            type.
        title (str):
            Optional. Title for the schema.
        description (str):
            Optional. Description of the schema.
        nullable (bool):
            Optional. Indicates if the value of this
            field can be null.
        default (google.protobuf.struct_pb2.Value):
            Optional. Default value to use if the field
            is not specified.
        items (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.Schema):
            Optional. If type is ``ARRAY``, ``items`` specifies the
            schema of elements in the array.
        min_items (int):
            Optional. If type is ``ARRAY``, ``min_items`` specifies the
            minimum number of items in an array.
        max_items (int):
            Optional. If type is ``ARRAY``, ``max_items`` specifies the
            maximum number of items in an array.
        enum (MutableSequence[str]):
            Optional. Possible values of the field. This field can be
            used to restrict a value to a fixed set of values. To mark a
            field as an enum, set ``format`` to ``enum`` and provide the
            list of possible values in ``enum``. For example:

            1. To define directions:
               ``{type:STRING, format:enum, enum:["EAST", "NORTH", "SOUTH", "WEST"]}``
            2. To define apartment numbers:
               ``{type:INTEGER, format:enum, enum:["101", "201", "301"]}``
        properties (MutableMapping[str, googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.Schema]):
            Optional. If type is ``OBJECT``, ``properties`` is a map of
            property names to schema definitions for each property of
            the object.
        property_ordering (MutableSequence[str]):
            Optional. Order of properties displayed or
            used where order matters. This is not a standard
            field in OpenAPI specification, but can be used
            to control the order of properties.
        required (MutableSequence[str]):
            Optional. If type is ``OBJECT``, ``required`` lists the
            names of properties that must be present.
        min_properties (int):
            Optional. If type is ``OBJECT``, ``min_properties``
            specifies the minimum number of properties that can be
            provided.
        max_properties (int):
            Optional. If type is ``OBJECT``, ``max_properties``
            specifies the maximum number of properties that can be
            provided.
        minimum (float):
            Optional. If type is ``INTEGER`` or ``NUMBER``, ``minimum``
            specifies the minimum allowed value.
        maximum (float):
            Optional. If type is ``INTEGER`` or ``NUMBER``, ``maximum``
            specifies the maximum allowed value.
        min_length (int):
            Optional. If type is ``STRING``, ``min_length`` specifies
            the minimum length of the string.
        max_length (int):
            Optional. If type is ``STRING``, ``max_length`` specifies
            the maximum length of the string.
        pattern (str):
            Optional. If type is ``STRING``, ``pattern`` specifies a
            regular expression that the string must match.
        example (google.protobuf.struct_pb2.Value):
            Optional. Example of an instance of this
            schema.
        any_of (MutableSequence[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.Schema]):
            Optional. The instance must be valid against any (one or
            more) of the subschemas listed in ``any_of``.
        additional_properties (google.protobuf.struct_pb2.Value):
            Optional. If ``type`` is ``OBJECT``, specifies how to handle
            properties not defined in ``properties``. If it is a boolean
            ``false``, no additional properties are allowed. If it is a
            schema, additional properties are allowed if they conform to
            the schema.
        ref (str):
            Optional. Allows referencing another schema definition to
            use in place of this schema. The value must be a valid
            reference to a schema in ``defs``.

            For example, the following schema defines a reference to a
            schema node named "Pet":

            type: object properties: pet: ref: #/defs/Pet defs: Pet:
            type: object properties: name: type: string

            The value of the "pet" property is a reference to the schema
            node named "Pet". See details in
            https://json-schema.org/understanding-json-schema/structuring
        defs (MutableMapping[str, googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1beta1.types.Schema]):
            Optional. ``defs`` provides a map of schema definitions that
            can be reused by ``ref`` elsewhere in the schema. Only
            allowed at root level of the schema.
    """

    type_: 'Type' = proto.Field(
        proto.ENUM,
        number=1,
        enum='Type',
    )
    format_: str = proto.Field(
        proto.STRING,
        number=7,
    )
    title: str = proto.Field(
        proto.STRING,
        number=24,
    )
    description: str = proto.Field(
        proto.STRING,
        number=8,
    )
    nullable: bool = proto.Field(
        proto.BOOL,
        number=6,
    )
    default: struct_pb2.Value = proto.Field(
        proto.MESSAGE,
        number=23,
        message=struct_pb2.Value,
    )
    items: 'Schema' = proto.Field(
        proto.MESSAGE,
        number=2,
        message='Schema',
    )
    min_items: int = proto.Field(
        proto.INT64,
        number=21,
    )
    max_items: int = proto.Field(
        proto.INT64,
        number=22,
    )
    enum: MutableSequence[str] = proto.RepeatedField(
        proto.STRING,
        number=9,
    )
    properties: MutableMapping[str, 'Schema'] = proto.MapField(
        proto.STRING,
        proto.MESSAGE,
        number=3,
        message='Schema',
    )
    property_ordering: MutableSequence[str] = proto.RepeatedField(
        proto.STRING,
        number=25,
    )
    required: MutableSequence[str] = proto.RepeatedField(
        proto.STRING,
        number=5,
    )
    min_properties: int = proto.Field(
        proto.INT64,
        number=14,
    )
    max_properties: int = proto.Field(
        proto.INT64,
        number=15,
    )
    minimum: float = proto.Field(
        proto.DOUBLE,
        number=16,
    )
    maximum: float = proto.Field(
        proto.DOUBLE,
        number=17,
    )
    min_length: int = proto.Field(
        proto.INT64,
        number=18,
    )
    max_length: int = proto.Field(
        proto.INT64,
        number=19,
    )
    pattern: str = proto.Field(
        proto.STRING,
        number=20,
    )
    example: struct_pb2.Value = proto.Field(
        proto.MESSAGE,
        number=4,
        message=struct_pb2.Value,
    )
    any_of: MutableSequence['Schema'] = proto.RepeatedField(
        proto.MESSAGE,
        number=11,
        message='Schema',
    )
    additional_properties: struct_pb2.Value = proto.Field(
        proto.MESSAGE,
        number=26,
        message=struct_pb2.Value,
    )
    ref: str = proto.Field(
        proto.STRING,
        number=27,
    )
    defs: MutableMapping[str, 'Schema'] = proto.MapField(
        proto.STRING,
        proto.MESSAGE,
        number=28,
        message='Schema',
    )


__all__ = tuple(sorted(__protobuf__.manifest))

# -*- coding: utf-8 -*-
# Copyright 2024 Google LLC
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
    package='google.cloud.aiplatform.v1',
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
    r"""Schema is used to define the format of input/output data. Represents
    a select subset of an `OpenAPI 3.0 schema
    object <https://spec.openapis.org/oas/v3.0.3#schema-object>`__. More
    fields may be added in the future as needed.

    Attributes:
        type_ (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.Type):
            Optional. The type of the data.
        format_ (str):
            Optional. The format of the data.
            Supported formats:

             for NUMBER type: "float", "double"
             for INTEGER type: "int32", "int64"
             for STRING type: "email", "byte", etc
        title (str):
            Optional. The title of the Schema.
        description (str):
            Optional. The description of the data.
        nullable (bool):
            Optional. Indicates if the value may be null.
        default (google.protobuf.struct_pb2.Value):
            Optional. Default value of the data.
        items (googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.Schema):
            Optional. SCHEMA FIELDS FOR TYPE ARRAY
            Schema of the elements of Type.ARRAY.
        min_items (int):
            Optional. Minimum number of the elements for
            Type.ARRAY.
        max_items (int):
            Optional. Maximum number of the elements for
            Type.ARRAY.
        enum (MutableSequence[str]):
            Optional. Possible values of the element of primitive type
            with enum format. Examples:

            1. We can define direction as : {type:STRING, format:enum,
               enum:["EAST", NORTH", "SOUTH", "WEST"]}
            2. We can define apartment number as : {type:INTEGER,
               format:enum, enum:["101", "201", "301"]}
        properties (MutableMapping[str, googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.Schema]):
            Optional. SCHEMA FIELDS FOR TYPE OBJECT
            Properties of Type.OBJECT.
        property_ordering (MutableSequence[str]):
            Optional. The order of the properties.
            Not a standard field in open api spec. Only used
            to support the order of the properties.
        required (MutableSequence[str]):
            Optional. Required properties of Type.OBJECT.
        min_properties (int):
            Optional. Minimum number of the properties
            for Type.OBJECT.
        max_properties (int):
            Optional. Maximum number of the properties
            for Type.OBJECT.
        minimum (float):
            Optional. SCHEMA FIELDS FOR TYPE INTEGER and
            NUMBER Minimum value of the Type.INTEGER and
            Type.NUMBER
        maximum (float):
            Optional. Maximum value of the Type.INTEGER
            and Type.NUMBER
        min_length (int):
            Optional. SCHEMA FIELDS FOR TYPE STRING
            Minimum length of the Type.STRING
        max_length (int):
            Optional. Maximum length of the Type.STRING
        pattern (str):
            Optional. Pattern of the Type.STRING to
            restrict a string to a regular expression.
        example (google.protobuf.struct_pb2.Value):
            Optional. Example of the object. Will only
            populated when the object is the root.
        any_of (MutableSequence[googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.Schema]):
            Optional. The value should be validated
            against any (one or more) of the subschemas in
            the list.
        additional_properties (google.protobuf.struct_pb2.Value):
            Optional. Can either be a boolean or an
            object; controls the presence of additional
            properties.
        ref (str):
            Optional. Allows indirect references between schema nodes.
            The value should be a valid reference to a child of the root
            ``defs``.

            For example, the following schema defines a reference to a
            schema node named "Pet":

            type: object properties: pet: ref: #/defs/Pet defs: Pet:
            type: object properties: name: type: string

            The value of the "pet" property is a reference to the schema
            node named "Pet". See details in
            https://json-schema.org/understanding-json-schema/structuring
        defs (MutableMapping[str, googlecloudsdk.generated_clients.gapic_clients.aiplatform_v1.types.Schema]):
            Optional. A map of definitions for use by ``ref`` Only
            allowed at the root of the schema.
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

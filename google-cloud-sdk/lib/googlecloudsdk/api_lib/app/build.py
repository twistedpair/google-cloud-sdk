# Copyright 2018 Google Inc. All Rights Reserved.
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
"""Utility classes for interacting with the Cloud Build API."""

import enum
from googlecloudsdk.api_lib.cloudbuild import build


class BuildArtifact(object):
  """Represents a build of a flex container, either in-progress or completed.

  A build artifact is either a build_id for an in-progress build, or the image
  name for a completed container build. If a build_id is used in a depoloyment,
  Flex serving infrastructure is brought up in parallel with the container
  build. When an image name is used instead, flex serving infrastructure is
  brought up in serial after the build has completed.
  """

  class BuildType(enum.Enum):
    IMAGE = 1
    BUILD_ID = 2

  def __init__(self, build_type, identifier, build_op=None):
    self.build_type = build_type
    self.identifier = identifier
    self.build_op = build_op

  def IsImage(self):
    return self.build_type == self.BuildType.IMAGE

  def IsBuildId(self):
    return self.build_type == self.BuildType.BUILD_ID

  @classmethod
  def MakeBuildIdArtifact(cls, build_id):
    return cls(cls.BuildType.BUILD_ID, build_id)

  @classmethod
  def MakeImageArtifact(cls, image_name):
    return cls(cls.BuildType.IMAGE, image_name)

  @classmethod
  def MakeBuildIdArtifactFromOp(cls, build_op):
    build_id = build.GetBuildProp(build_op, 'id', required=True)
    return cls(cls.BuildType.BUILD_ID, build_id, build_op)

  @classmethod
  def MakeImageArtifactFromOp(cls, build_op):
    """Create Image BuildArtifact from build operation."""
    source = build.GetBuildProp(build_op, 'source')
    for prop in source.object_value.properties:
      if prop.key == 'storageSource':
        for storage_prop in prop.value.object_value.properties:
          if storage_prop.key == 'object':
            image_name = storage_prop.value.string_value

    if image_name is None:
      raise build.BuildFailedError('Could not determine image name')

    return cls(cls.BuildType.IMAGE, image_name, build_op)
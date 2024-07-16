# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Helper functions for constructing API requests for conversion workspaces."""


import os


def GetTargetFileNameForApplicationCode(
    source_file: str, target_path: str
) -> str:
  """Returns the target file name for the application code."""
  source_file_name = os.path.basename(source_file)
  if target_path is None:
    # target path is not specified, overwrite the source file
    return source_file
  elif os.path.isdir(target_path):
    # target path is a directory, write the converted code in the target
    # directory with the same name as the source file.
    return os.path.join(target_path, source_file_name)
  else:
    # target path is a file, write the converted code in the target file.
    return target_path

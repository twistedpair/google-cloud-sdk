# Copyright 2016 Google Inc. All Rights Reserved.
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

"""This module holds exceptions raised by api lib."""

from googlecloudsdk.core import exceptions


class NotFoundError(exceptions.Error):
  """Raised when the requested resource does not exist."""


class ConflictError(exceptions.Error):
  """Raised when a new resource already exists."""


class ConfigError(exceptions.Error):
  """Raised when unable to parse a config file."""


class StorageError(exceptions.Error):
  """Raised when the syncing with storage errors."""


class DeleteError(exceptions.Error):
  """Raised when deletes fail."""


STATUS_CODE_TO_ERROR = {
    404: NotFoundError,
    409: ConflictError
}

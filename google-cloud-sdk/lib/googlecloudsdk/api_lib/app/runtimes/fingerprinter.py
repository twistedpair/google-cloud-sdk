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

"""Package containing fingerprinting for all runtimes.
"""

from googlecloudsdk.api_lib.app import ext_runtime
from googlecloudsdk.api_lib.app.ext_runtimes import fingerprinting
from googlecloudsdk.api_lib.app.runtimes import aspnet
from googlecloudsdk.api_lib.app.runtimes import go
from googlecloudsdk.api_lib.app.runtimes import java
from googlecloudsdk.api_lib.app.runtimes import python
from googlecloudsdk.api_lib.app.runtimes import python_compat
from googlecloudsdk.api_lib.app.runtimes import ruby
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log

RUNTIMES = [
    # Note that ordering of runtimes here is very important and changes to the
    # relative positions need to be tested carefully.
    go,  # Go's position is relatively flexible due to its orthogonal nature.
    ruby,
    ext_runtime.CoreRuntimeLoader('nodejs', 'Node.js', ['nodejs', 'custom']),
    java,
    python_compat,
    aspnet,
    python,  # python is last because it passes if there are any .py files.
]


class UnidentifiedDirectoryError(exceptions.Error):
  """Raised when GenerateConfigs() can't identify the directory."""

  def __init__(self, path):
    """Constructor.

    Args:
      path: (basestring) Directory we failed to identify.
    """
    super(UnidentifiedDirectoryError, self).__init__(
        'Unrecognized directory type: [{0}]'.format(path))
    self.path = path


def IdentifyDirectory(path, params=None):
  """Try to identify the given directory.

  As a side-effect, if there is a config file in 'params' with a runtime of
  'custom', this sets params.custom to True.

  Args:
    path: (basestring) Root directory to identify.
    params: (fingerprinting.Params or None) Parameters passed through to the
      fingerprinters.  Uses defaults if not provided.

  Returns:
    (fingerprinting.Module or None) Returns a module if we've identified it,
    None if not.
  """
  specified_runtime = None
  if not params:
    params = fingerprinting.Params()
  elif params.appinfo:
    specified_runtime = params.appinfo.GetEffectiveRuntime()
    if specified_runtime == 'custom':
      params.custom = True

  for runtime in RUNTIMES:

    # If we have an app.yaml, don't fingerprint for any runtimes that don't
    # allow the runtime name it specifies.
    if (specified_runtime and runtime.ALLOWED_RUNTIME_NAMES and
        specified_runtime not in runtime.ALLOWED_RUNTIME_NAMES):
      log.info('Not checking for [%s] because runtime is [%s]' %
               (runtime.NAME, specified_runtime))
      continue

    configurator = runtime.Fingerprint(path, params)
    if configurator:
      return configurator
  return None


def GenerateConfigs(path, params=None):
  """Generate all config files for the path into the current directory.

  As a side-effect, if there is a config file in 'params' with a runtime of
  'custom', this sets params.custom to True.

  Args:
    path: (basestring) Root directory to identify.
    params: (fingerprinting.Params or None) Parameters passed through to the
      fingerprinters.  Uses defaults if not provided.

  Raises:
    UnidentifiedDirectoryError: No runtime module matched the directory.

  Returns:
    (callable()) Function to remove all generated files (if desired).
  """
  if not params:
    params = fingerprinting.Params()
  module = IdentifyDirectory(path, params)
  if not module:
    raise UnidentifiedDirectoryError(path)

  return module.GenerateConfigs()

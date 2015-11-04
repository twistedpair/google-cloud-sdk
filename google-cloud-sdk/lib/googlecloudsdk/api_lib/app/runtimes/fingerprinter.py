# Copyright 2015 Google Inc. All Rights Reserved.

"""Package containing fingerprinting for all runtimes.
"""

from googlecloudsdk.api_lib.app.ext_runtimes import fingerprinting
from googlecloudsdk.api_lib.app.runtimes import go
from googlecloudsdk.api_lib.app.runtimes import java
from googlecloudsdk.api_lib.app.runtimes import nodejs
from googlecloudsdk.api_lib.app.runtimes import python
from googlecloudsdk.api_lib.app.runtimes import ruby
from googlecloudsdk.core import exceptions

# TODO(mmuller): add some runtimes to this.
RUNTIMES = [
    # Note that ordering of runtimes here is very important and changes to the
    # relative positions need to be tested carefully.
    go,  # Go's position is relatively flexible due to its orthogonal nature.
    ruby,
    nodejs,
    java,
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
        'Unrecognized directory type: [{}]'.format(path))
    self.path = path


def IdentifyDirectory(path, params=None):
  """Try to identify the given directory.

  Args:
    path: (basestring) Root directory to identify.
    params: (fingerprinting.Params or None) Parameters passed through to the
      fingerprinters.  Uses defaults if not provided.

  Returns:
    (fingerprinting.Module or None) Returns a module if we've identified it,
    None if not.
  """
  if not params:
    params = fingerprinting.Params()
  for runtime in RUNTIMES:
    configurator = runtime.Fingerprint(path, params)
    if configurator:
      return configurator
  return None


def GenerateConfigs(path, params=None):
  """Generate all config files for the path into the current directory.

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

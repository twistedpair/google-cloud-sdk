# Copyright 2015 Google Inc. All Rights Reserved.

"""Fingerprinting code for the Go runtime."""

import atexit
import fnmatch
import os
import re
import textwrap

from googlecloudsdk.core import log

from googlecloudsdk.appengine.lib import fingerprinting
from googlecloudsdk.appengine.lib.images import config
from googlecloudsdk.appengine.lib.images import util

GO_RUNTIME_NAME = 'go'

GO_APP_YAML = textwrap.dedent("""\
    vm: true
    runtime: {runtime}
    api_version: go1
    """)
DOCKERIGNORE = textwrap.dedent("""\
    .dockerignore
    Dockerfile
    .git
    .hg
    .svn
    """)


class GoConfigurator(fingerprinting.Configurator):
  """Generates configuration for a Go app."""

  def __init__(self, path, params):
    """Constructor.

    Args:
      path: (str) Root path of the source tree.
      params: (fingerprinting.Params) Parameters passed through to the
        fingerprinters.
    """

    self.root = path
    self.params = params

  def GenerateConfigs(self):
    """Generate all config files for the module.

    Returns:
      (callable()) fingerprinting.Cleaner instance.
    """
    # Write "Saving file" messages to the user or to log depending on whether
    # we're in "deploy."
    if self.params.deploy:
      notify = log.info
    else:
      notify = log.status.Print

    # Generate app.yaml.
    cleaner = fingerprinting.Cleaner()
    if not self.params.deploy:
      app_yaml = os.path.join(self.root, 'app.yaml')
      if not os.path.exists(app_yaml):
        notify('Saving [app.yaml] to [%s].' % self.root)
        runtime = 'custom' if self.params.custom else 'go'
        with open(app_yaml, 'w') as f:
          f.write(GO_APP_YAML.format(runtime=runtime))
        cleaner.Add(app_yaml)

    if self.params.custom or self.params.deploy:
      dockerfile = os.path.join(self.root, config.DOCKERFILE)
      if not os.path.exists(dockerfile):
        notify('Saving [%s] to [%s].' % (config.DOCKERFILE, self.root))
        util.FindOrCopyDockerfile(GO_RUNTIME_NAME, self.root,
                                  cleanup=self.params.deploy)
        cleaner.Add(dockerfile)

      # Generate .dockerignore TODO(user): eventually this file will just be
      # copied verbatim.
      dockerignore = os.path.join(self.root, '.dockerignore')
      if not os.path.exists(dockerignore):
        notify('Saving [.dockerignore] to [%s].' % self.root)
        with open(dockerignore, 'w') as f:
          f.write(DOCKERIGNORE)
        cleaner.Add(dockerignore)

        if self.params.deploy:
          atexit.register(util.Clean, dockerignore)

    if not cleaner.HasFiles():
      notify('All config files already exist, not generating anything.')

    return cleaner


def _GoFiles(path):
  """Return list of '*.go' files under directory 'path'.

  Note that os.walk by default performs a top-down search, so files higher in
  the directory tree appear before others.

  Args:
    path: (str) Application path.

  Returns:
    ([str, ...]) List of full pathnames for all '*.go' files under 'path' dir.
  """
  go_files = []
  for root, _, filenames in os.walk(path):
    for filename in fnmatch.filter(filenames, '*.go'):
      go_files.append(os.path.join(root, filename))
  return go_files


def _FindMain(filename):
  """Check filename for 'package main' and 'func main'.

  Args:
    filename: (str) File name to check.

  Returns:
    (bool) True if main is found in filename.
  """
  with open(filename) as f:
    found_package = False
    found_func = False
    for line in f:
      if re.match('^package main', line):
        found_package = True
      elif re.match('^func main', line):
        found_func = True
      if found_package and found_func:
        return True
  return False


def Fingerprint(path, params):
  """Check for a Go app.

  Args:
    path: (str) Application path.
    params: (fingerprinting.Params) Parameters passed through to the
      fingerprinters.

  Returns:
    (GoConfigurator or None) Returns a module if the path contains a
    Go app.
  """
  log.info('Checking for Go.')

  # Test #1 - are there any '*.go' files at or below 'path'?
  go_files = _GoFiles(path)
  if not go_files:
    return None

  # Test #2 - check that one of these files has "package main" and "func main".
  main_found = False
  for f in go_files:
    if _FindMain(f):
      log.info('Found Go main in %s', f)
      main_found = True
      break
  if not main_found:
    return None

  return GoConfigurator(path, params)

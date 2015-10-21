# Copyright 2014 Google Inc. All Rights Reserved.

"""Helper Functions for appengine.lib.images module."""

import atexit
import os

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.util import pkg_resources

import googlecloudsdk.appengine
from googlecloudsdk.appengine.lib.images import config


class NoDefaultDockerfileError(exceptions.Error):
  """No default Dockerfile for a given runtime."""


class NoDockerfileError(exceptions.Error):
  """No Dockerfile found (neither user provided, nor default)."""


def FindOrCopyDockerfile(runtime, dst, cleanup=True):
  """Copies default Dockerfile for a given runtime into destination directory.

  Default Dockerfile for runtime is used if there is no user provided dockerfile
  in the destination directory.

  Args:
    runtime: str, Runtime that we're looking for the Dockerfile for.
    dst: str, Directory path where to check for and copy to the Dockerfile.
    cleanup: bool, If true, delete the file on gcloud exit.

  Raises:
    IOError: raised by pkg_resources.GetData if the Dockerfile doesn't exist
      in the expected location.

  Returns:
    callable(), A function to be called to clean up the generated Dockerfile.
  """
  log.info('Looking for the %s in %s', config.DOCKERFILE, dst)
  if os.path.exists(os.path.join(dst, config.DOCKERFILE)):
    log.info('Using %s found in %s', config.DOCKERFILE, dst)
    return lambda: None
  log.info('Looking for the default %s for runtime [%s]',
           config.DOCKERFILE, runtime)
  runtime = _GetCanonicalRuntime(runtime)
  default_dockerfiles_dir = GetGCloudDockerfilesDir()
  src = os.path.join(
      default_dockerfiles_dir,
      '{runtime}_app'.format(runtime=runtime),
      config.DOCKERFILE)
  src_data = pkg_resources.GetData(src)
  log.info('%s for runtime [%s] is found in %s. Copying it into application '
           'directory.', config.DOCKERFILE, runtime, default_dockerfiles_dir)
  with open(os.path.join(dst, os.path.basename(src)), 'w') as dst_file:
    dst_file.write(src_data)
  # Delete the file after we're done if necessary.
  if cleanup:
    full_name = os.path.join(dst, config.DOCKERFILE)
    atexit.register(Clean, full_name)
    return lambda: Clean(full_name)
  return lambda: None


def GetAllManagedVMsRuntimes():
  """Returns the list of runtimes supported by Managed VMs.

  The list of supported runtimes is built based on the default Dockerfiles
  provided with the SDK.

  Raises:
    InternalError: if there is no directory with default Dockerfiles.

  Returns:
    [str], List of runtimes supported for Managed VMs.
  """
  dockerfiles_dir = GetGCloudDockerfilesDir()
  resources = pkg_resources.ListPackageResources(dockerfiles_dir)
  # Strips trailing '_app/'.
  dockerfile_runtimes = [x[:-5] for x in resources if not x.startswith('.')]

  # We also support mappings from other strings to these runtime IDs.
  # java7->java, for example.
  return dockerfile_runtimes + config.CANONICAL_RUNTIMES.keys()


def _GetCanonicalRuntime(runtime):
  """Retuns canonical runtime name (might be equal to the given value)."""
  res = config.CANONICAL_RUNTIMES.get(runtime, runtime)
  if res != runtime:
    log.info(
        'Runtime [{runtime}] is substituted by [{canonical_runtime}]'.format(
            runtime=runtime, canonical_runtime=res))
  return res


def GetGCloudDockerfilesDir():
  """Retuns path containing default Dockerfiles for Managed VMs apps.

  Returns:
    str, The path with default Dockerfiles for Managed VMs runtimes.
  """
  return os.path.join(
      os.path.dirname(googlecloudsdk.appengine.__file__), 'dockerfiles')


def Clean(path):
  try:
    if os.path.exists(path):
      os.remove(path)
  except OSError as e:
    log.debug('Error removing generated %s: %s', path, e)

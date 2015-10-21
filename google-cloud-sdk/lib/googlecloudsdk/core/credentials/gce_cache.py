# Copyright 2013 Google Inc. All Rights Reserved.

"""Caching logic for checking if we're on GCE."""

import os
from threading import Lock
import time
import urllib2

from googlecloudsdk.core import config
from googlecloudsdk.core.credentials import gce_read
from googlecloudsdk.core.util import files

_GCE_CACHE_MAX_AGE = 10*60  # 10 minutes


class _OnGCECache(object):
  """Logic to check if we're on GCE and cache the result to file or memory.

  Checking if we are on GCE is done by issuing an HTTP request to a GCE server.
  Since HTTP requests are slow, we cache this information. Because every run
  of gcloud is a separate command, the cache is stored in a file in the user's
  gcloud config dir. Because within a gcloud run we might check if we're on GCE
  multiple times, we also cache this information in memory.
  A user can move the gcloud instance to and from a GCE VM, and the GCE server
  can sometimes not respond. Therefore the cache has an age and gets refreshed
  if more than _GCE_CACHE_MAX_AGE passed since it was updated.
  """

  def __init__(self):
    self.connected = None
    self.mtime = None
    self.file_lock = Lock()

  def GetOnGCE(self, check_age=True):
    """Check if we are on a GCE machine.

    Check the memory cache if we're on GCE. If the cache is not populated,
    update it.
    If check_age is True, then update all caches if the information we have is
    older than _GCE_CACHE_MAX_AGE. In most cases, age should be respected. It
    was added for reporting metrics.

    Args:
      check_age: bool, determines if the cache should be refreshed if more than
          _GCE_CACHE_MAX_AGE time passed since last update.

    Returns:
      bool, if we are on GCE or not.
    """
    if self.connected is None or self.mtime is None:
      self._UpdateMemory()
    if check_age and time.time() - self.mtime > _GCE_CACHE_MAX_AGE:
      self._UpdateFileCache()
      self._UpdateMemory()
    return self.connected

  def _UpdateMemory(self):
    """Read from file and store in memory."""
    gce_cache_path = config.Paths().GCECachePath()
    if not os.path.exists(gce_cache_path):
      self._UpdateFileCache()
    with self.file_lock:
      self.mtime = os.stat(gce_cache_path).st_mtime
      with open(gce_cache_path) as gcecache_file:
        self.connected = gcecache_file.read() == str(True)

  def _UpdateFileCache(self):
    """Check server if connected, write the result to file."""
    gce_cache_path = config.Paths().GCECachePath()
    on_gce = self._CheckServer()
    with self.file_lock:
      with files.OpenForWritingPrivate(gce_cache_path) as gcecache_file:
        gcecache_file.write(str(on_gce))

  def _CheckServer(self):
    try:
      numeric_project_id = gce_read.ReadNoProxy(
          gce_read.GOOGLE_GCE_METADATA_NUMERIC_PROJECT_URI)
    except (urllib2.HTTPError, urllib2.URLError):
      return False
    else:
      return numeric_project_id.isdigit()

# Since a module is initialized only once, this is effective a singleton
_SINGLETON_ON_GCE_CACHE = _OnGCECache()


def GetOnGCE(check_age=True):
  """Helper function to abstract the caching logic of if we're on GCE."""
  return _SINGLETON_ON_GCE_CACHE.GetOnGCE(check_age)

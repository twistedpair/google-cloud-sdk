# Copyright 2015 Google Inc. All Rights Reserved.

"""A decorator around urlopen that provides appropriate CA certs."""

import inspect
import httplib2

try:
  # Python3 urllib
  # pylint: disable=g-import-not-at-top
  from urllib.request import urlopen as orig_urlopen
except ImportError:
  # Python2 urllib
  # pylint: disable=g-import-not-at-top
  from urllib2 import urlopen as orig_urlopen


CAFILE_ARG = 'cafile'


def urlopen(*args, **kwargs):
  # Check whether this urlopen version accepts cacerts file.
  orig_urlopen_args = inspect.getargspec(orig_urlopen).args
  if CAFILE_ARG in orig_urlopen_args:
    # Provide the cacerts file used by httplib2 while calling urlopen.
    kwargs[CAFILE_ARG] = httplib2.CA_CERTS
  return orig_urlopen(*args, **kwargs)

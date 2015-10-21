# Copyright 2013 Google Inc. All Rights Reserved.

"""Utility functions for opening a GCE URL and getting contents."""

import urllib2


GOOGLE_GCE_METADATA_URI = 'http://metadata.google.internal/computeMetadata/v1'

GOOGLE_GCE_METADATA_DEFAULT_ACCOUNT_URI = (
    GOOGLE_GCE_METADATA_URI + '/instance/service-accounts/default/email')

GOOGLE_GCE_METADATA_PROJECT_URI = (
    GOOGLE_GCE_METADATA_URI + '/project/project-id')

GOOGLE_GCE_METADATA_NUMERIC_PROJECT_URI = (
    GOOGLE_GCE_METADATA_URI + '/project/numeric-project-id')

GOOGLE_GCE_METADATA_ACCOUNTS_URI = (
    GOOGLE_GCE_METADATA_URI + '/instance/service-accounts')

GOOGLE_GCE_METADATA_ACCOUNT_URI = (
    GOOGLE_GCE_METADATA_ACCOUNTS_URI + '/{account}/email')

GOOGLE_GCE_METADATA_ZONE_URI = (
    GOOGLE_GCE_METADATA_URI + '/instance/zone')

GOOGLE_GCE_METADATA_HEADERS = {'Metadata-Flavor': 'Google'}


def ReadNoProxy(uri):
  """Opens a URI with metadata headers, without a proxy, and reads all data.."""
  request = urllib2.Request(uri, headers=GOOGLE_GCE_METADATA_HEADERS)
  return urllib2.build_opener(urllib2.ProxyHandler({})).open(
      request, timeout=1).read()

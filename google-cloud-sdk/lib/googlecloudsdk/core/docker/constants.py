# Copyright 2014 Google Inc. All Rights Reserved.

"""Default value constants exposed by core utilities."""

DEFAULT_REGISTRY = 'gcr.io'
REGIONAL_REGISTRIES = ['us.gcr.io', 'eu.gcr.io', 'asia.gcr.io']
BUCKET_REGISTRIES = ['b.gcr.io', 'bucket.gcr.io']
APPENGINE_REGISTRY = 'appengine.gcr.io'
SPECIALTY_REGISTRIES = BUCKET_REGISTRIES + [APPENGINE_REGISTRY]
ALL_SUPPORTED_REGISTRIES = ([DEFAULT_REGISTRY] + REGIONAL_REGISTRIES
                            + SPECIALTY_REGISTRIES)
DEFAULT_DEVSHELL_IMAGE = (DEFAULT_REGISTRY +
                          '/dev_con/cloud-dev-common:prod')
METADATA_IMAGE = DEFAULT_REGISTRY + '/google_appengine/faux-metadata:latest'

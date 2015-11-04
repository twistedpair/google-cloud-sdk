# Copyright 2015 Google Inc. All Rights Reserved.

"""Constants for the dataproc tool."""

# TODO(pclay): Move defaults to the server
from googlecloudsdk.third_party.apis.dataproc.v1beta1 import dataproc_v1beta1_messages as messages

# Job Status states that do not change.
TERMINAL_JOB_STATES = [
    messages.JobStatus.StateValueValuesEnum.CANCELLED,
    messages.JobStatus.StateValueValuesEnum.DONE,
    messages.JobStatus.StateValueValuesEnum.ERROR,
]

# Path inside of GCS bucket to stage files.
GCS_STAGING_PREFIX = 'google-cloud-dataproc-staging'

# Beginning of driver output files.
JOB_OUTPUT_PREFIX = 'driveroutput'

# The scopes that will be added to user-specified scopes. Used for
# documentation only. Keep in sync with server specified list.
MINIMUM_SCOPE_URIS = [
    'https://www.googleapis.com/auth/cloud.useraccounts.readonly',
    'https://www.googleapis.com/auth/devstorage.read_write',
    'https://www.googleapis.com/auth/logging.write',
]

# The scopes that will be specified by default. Used fo documentation only.
# Keep in sync with server specified list.
ADDITIONAL_DEFAULT_SCOPE_URIS = [
    'https://www.googleapis.com/auth/bigquery',
    'https://www.googleapis.com/auth/bigtable.admin.table',
    'https://www.googleapis.com/auth/bigtable.data',
    'https://www.googleapis.com/auth/devstorage.full_control',
]

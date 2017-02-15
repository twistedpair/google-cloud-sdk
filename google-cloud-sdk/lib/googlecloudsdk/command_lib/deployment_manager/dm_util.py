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

"""Util functions for DM commands."""
import base64

from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import log


def PrintFingerprint(fingerprint):
  """Print the fingerprint for user reference."""

  log.status.Print('The fingerprint of the deployment is %s'
                   % (base64.urlsafe_b64encode(fingerprint)))


def DecodeFingerprint(fingerprint):
  """Returns the base64 url decoded fingerprint."""
  try:
    decoded_fingerprint = base64.urlsafe_b64decode(fingerprint)
  except TypeError:
    raise calliope_exceptions.InvalidArgumentException(
        '--fingerprint', 'fingerprint cannot be decoded.')
  return decoded_fingerprint

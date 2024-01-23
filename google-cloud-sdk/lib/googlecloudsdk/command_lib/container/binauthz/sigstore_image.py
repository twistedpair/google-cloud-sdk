# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Utilities for working with Sigstore style attestations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import base64
import json

from googlecloudsdk.core.exceptions import Error


def StandardOrUrlsafeBase64Decode(encoded):
  try:
    return base64.b64decode(encoded)
  except Error:
    return base64.urlsafe_b64decode(encoded)


def AttestationToImageUrl(attestation):
  """Extract the image url from a DSSE of predicate type https://binaryauthorization.googleapis.com/policy_verification/*.

  This is a helper function for mapping attestations back to their respective
  imaged. Do not use this for signature verification.

  Args:
    attestation: The attestation in base64 encoded string form.

  Returns:
    The image url referenced in the attestation.
  """
  # The DSSE spec permits either standard or URL-safe base64 encoding.
  deser_att = json.loads(StandardOrUrlsafeBase64Decode(attestation))

  deser_payload = json.loads(
      StandardOrUrlsafeBase64Decode(deser_att['payload'])
  )
  return '{}@sha256:{}'.format(
      deser_payload['subject'][0]['name'],
      deser_payload['subject'][0]['digest']['sha256'],
  )

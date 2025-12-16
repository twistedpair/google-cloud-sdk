# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Helpers for parsing key files in pem format."""


from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import base64

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core.util import files
import six


def GetPemPublicKey(public_key_file):
  """Reads, validates, and returns the public key in PEM encoding within a file.

  Args:
    public_key_file: A public key file handle that contains a PEM encoded public
      key.

  Returns:
    The public key in PEM encoding.
  """
  data = files.ReadBinaryFileContents(public_key_file)
  if b'-----BEGIN PUBLIC KEY-----' in data:
    publickeyb64 = data.replace(b'-----BEGIN PUBLIC KEY-----', b'', 1)
    publickeyb64 = publickeyb64.replace(b'-----END PUBLIC KEY-----', b'', 1)
    # If there's another public key detected afterwards
    if b'-----BEGIN PUBLIC KEY-----' in publickeyb64:
      raise exceptions.BadArgumentException(
          'public_key_file',
          'Cannot place multiple public keys in the same file : {}'.format(
              public_key_file
          ),
      )
    try:
      publickeyb64 = publickeyb64.replace(b'\r', b'').replace(b'\n', b'')
      decoded = base64.b64decode(six.ensure_binary(publickeyb64))
      encoded = base64.b64encode(decoded)
      if encoded != publickeyb64:
        raise ValueError('Non-base64 digit found.')
    except Exception as e:
      raise exceptions.BadArgumentException(
          'public_key_file',
          'Recognized {} as a PEM encoded public key, but failed during'
          ' parsing : {}'.format(public_key_file, e),
      )
    return '\n'.join(data.decode('ascii').splitlines()) + '\n'
  else:
    raise exceptions.BadArgumentException(
        'public_key_file', 'Missing PEM public key header in file'
    )

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
"""Common classes and functions for network policy rules."""

from __future__ import absolute_import
from __future__ import annotations
from __future__ import division
from __future__ import unicode_literals

import dataclasses
import re

from googlecloudsdk.command_lib.compute import exceptions


ALLOWED_METAVAR = 'PROTOCOL[:PORT[-PORT]]'
LEGAL_SPECS = re.compile(
    r"""

    (?P<protocol>[a-zA-Z0-9+.-]+) # The protocol group.

    (:(?P<ports>\d+(-\d+)?))?     # The optional ports group.
                                  # May specify a range.

    $                             # End of input marker.
    """,
    re.VERBOSE,
)


class Layer4ConfigParsingError(Exception):
  """Raised when layer4 config parsing fails."""


@dataclasses.dataclass(frozen=True)
class Layer4Config:
  ip_protocol: str
  ports: str | None


def ParseLayer4Config(layer4_config: str) -> Layer4Config:
  """Parses protocol:port mappings for --layer4-configs command line."""
  match = LEGAL_SPECS.match(layer4_config)
  if not match:
    raise exceptions.ArgumentError(
        f'Layer4 config must be of the form {ALLOWED_METAVAR}; '
        f'received [{layer4_config}].'
    )

  ip_protocol = match.group('protocol')
  ports = match.group('ports')

  return Layer4Config(ip_protocol=ip_protocol, ports=ports)

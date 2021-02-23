# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Logging gRPC client.

This hand-written class is used as a placeholder so that we can start to add
functionality to gRPC clients used by gcloud such as credentials,
instrumentation like http logging and metrics reporting, and understand how
these clients are to be instantiated and used.

Eventually, the automated API client generation process will generate these
wrapper classes.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import gapic_util

try:
  # pylint: disable=g-import-not-at-top
  from googlecloudsdk.third_party import logging_v2
  from googlecloudsdk.third_party.logging_v2.gapic.transports.config_service_v2_grpc_transport import ConfigServiceV2GrpcTransport
  from googlecloudsdk.third_party.logging_v2.gapic.transports.logging_service_v2_grpc_transport import LoggingServiceV2GrpcTransport
  from googlecloudsdk.third_party.logging_v2.gapic.transports.metrics_service_v2_grpc_transport import MetricsServiceV2GrpcTransport
except ImportError:
  raise gapic_util.NoGRPCInstalledError()


class LoggingClient(object):
  """Logging client."""
  types = logging_v2.types

  def __init__(self, address_override=None):
    self.config = gapic_util.MakeClient(
        ConfigServiceV2GrpcTransport, logging_v2.ConfigServiceV2Client,
        address=address_override)
    self.logging = gapic_util.MakeClient(
        LoggingServiceV2GrpcTransport, logging_v2.LoggingServiceV2Client,
        address=address_override)
    self.metrics = gapic_util.MakeClient(
        MetricsServiceV2GrpcTransport, logging_v2.MetricsServiceV2Client,
        address=address_override)

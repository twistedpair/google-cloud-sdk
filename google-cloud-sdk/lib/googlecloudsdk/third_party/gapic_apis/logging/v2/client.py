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
from googlecloudsdk.third_party import logging_v2


class LoggingClient(object):
  """Logging client."""
  types = logging_v2.types

  def __init__(self):
    self.config = gapic_util.MakeClient(
        logging_v2.services.config_service_v2.client.ConfigServiceV2Client)
    self.logging = gapic_util.MakeClient(
        logging_v2.services.logging_service_v2.client.LoggingServiceV2Client)
    self.metrics = gapic_util.MakeClient(
        logging_v2.services.metrics_service_v2.client.MetricsServiceV2Client)

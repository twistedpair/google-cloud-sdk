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
"""Worker Pool Revision specific printer."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.api_lib.run import container_resource
from googlecloudsdk.api_lib.run import revision
from googlecloudsdk.command_lib.run.printers import container_and_volume_printer_util as container_util
from googlecloudsdk.command_lib.run.printers import k8s_object_printer_util as k8s_util
from googlecloudsdk.core.resource import custom_printer_base as cp

REVISION_PRINTER_FORMAT = 'revision'
CPU_ALWAYS_ALLOCATED_MESSAGE = 'CPU is always allocated'
EXECUTION_ENV_VALS = {'gen1': 'First Generation', 'gen2': 'Second Generation'}


class WorkerPoolRevisionPrinter(cp.CustomPrinterBase):
  """Prints the run Revision in a custom human-readable format.

  Format specific to Cloud Run revisions. Only available on Cloud Run commands
  that print revisions.
  """

  def Transform(self, record):
    """Transform a revision into the output structure of marker classes."""
    fmt = cp.Lines([
        k8s_util.BuildHeader(record),
        k8s_util.GetLabels(record.labels),
        ' ',
        self.TransformSpec(record),
        k8s_util.FormatReadyMessage(record),
    ])
    return fmt

  @staticmethod
  def GetCMEK(record):
    cmek_key = record.annotations.get(container_resource.CMEK_KEY_ANNOTATION)
    if not cmek_key:
      return ''
    cmek_name = cmek_key.split('/')[-1]
    return cmek_name

  @staticmethod
  def GetThreatDetectionEnabled(record):
    return k8s_util.GetThreatDetectionEnabled(record)

  @staticmethod
  def TransformSpec(record: revision.Revision) -> cp.Lines:
    labels = [('Service account', record.spec.serviceAccountName)]
    labels.extend([
        (
            'SQL connections',
            k8s_util.GetCloudSqlInstances(record.annotations),
        ),
        ('VPC access', k8s_util.GetVpcNetwork(record.annotations)),
        ('CMEK', WorkerPoolRevisionPrinter.GetCMEK(record)),
        ('Volumes', container_util.GetVolumes(record)),
        (
            'Threat Detection',
            WorkerPoolRevisionPrinter.GetThreatDetectionEnabled(record),
        ),
    ])
    return cp.Lines([container_util.GetContainers(record), cp.Labeled(labels)])
